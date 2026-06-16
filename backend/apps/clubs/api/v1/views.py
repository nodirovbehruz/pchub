from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clubs.api.v1.serializers import ClubCreateSerializer, ClubSerializer, ClubUpdateSerializer
from apps.clubs.models import Club, ClubMembership, ClubSettings, ClubSubscription, SubscriptionStatus


# Visual, non-sensitive keys exposed to / pushed at the shell (same whitelist the
# public branding endpoint serves).
BRANDING_KEYS = (
    "shell_background", "shell_background_url", "shell_bg_color",
    "tint_enabled", "tint_color", "accent_color", "secondary_color",
    "logo_url",
)


def _broadcast_branding(club_id, data: dict) -> None:
    """Push the current branding subset to every shell in the club (live recolor)."""
    try:
        from realtime.broadcast import push_theme
        push_theme(club_id, {k: data[k] for k in BRANDING_KEYS if k in data})
    except Exception:
        pass  # realtime is best-effort; shells still refresh theme on next login


@extend_schema(tags=["Clubs"])
class MyClubsListView(generics.ListCreateAPIView):
    """List clubs accessible by the current user (owned + active membership).

    POST: create a new club owned by the current user.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ClubCreateSerializer
        return ClubSerializer

    def get_queryset(self):
        user = self.request.user
        # ONLY platform-level admins (user_type='admin') see ALL clubs.
        # Club owners have is_superuser=True but must NOT see other owners' clubs.
        if getattr(user, 'user_type', None) == 'admin':
            return Club.objects.filter(is_active=True).order_by("name")
        # Everyone else: owned clubs + clubs where they have an active membership
        owned_ids = Club.objects.filter(owner=user, is_active=True).values_list("id", flat=True)
        member_ids = ClubMembership.objects.filter(
            user=user, is_active=True, club__is_active=True
        ).values_list("club_id", flat=True)
        ids = set(owned_ids) | set(member_ids)
        return Club.objects.filter(id__in=ids).order_by("name")

    def list(self, request, *args, **kwargs):
        # Attach the requesting user's per-club role so the frontend can gate by it
        # (tokens carry no role claim → Login.jsx otherwise defaulted everyone to
        # 'operator'). owner → 'owner', else the ClubMembership role.
        resp = super().list(request, *args, **kwargs)
        try:
            user = request.user
            owned = set(Club.objects.filter(owner=user).values_list("id", flat=True))
            roles = dict(
                ClubMembership.objects.filter(user=user, is_active=True)
                .values_list("club_id", "role")
            )
            items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
            for it in items:
                cid = it.get("id")
                it["role"] = "owner" if cid in owned else roles.get(cid, "operator")
        except Exception:
            pass
        return resp

    def perform_create(self, serializer):
        """Set owner to current user on club creation."""
        from django.utils import timezone

        trial_until = timezone.now() + timezone.timedelta(days=14)
        club = serializer.save(owner=self.request.user, is_trial=True, trial_until=trial_until)

        # Auto-create default ClubSettings
        try:
            ClubSettings.objects.get_or_create(club=club)
        except Exception:
            pass

        # Auto-create trial ClubSubscription record
        try:
            from apps.clubs.models import ClubSubscription, SubscriptionPlan, SubscriptionStatus
            free_plan, _ = SubscriptionPlan.objects.get_or_create(
                tier="free",
                defaults={"name": "Free", "monthly_price": 0, "max_pcs": 0},
            )
            ClubSubscription.objects.get_or_create(
                club=club,
                defaults={
                    "plan": free_plan,
                    "status": SubscriptionStatus.TRIAL,
                    "expires_at": trial_until,
                },
            )
        except Exception:
            pass

        return club

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        club = self.perform_create(serializer)
        return Response(
            ClubSerializer(club, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Clubs"])
class ClubRetrieveUpdateAPIView(APIView):
    """Retrieve or partially update a club. Owner/admin only for updates."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_club(self, pk, user):
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return None, Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        return club, None

    def get(self, request, pk):
        club, err = self._get_club(pk, request.user)
        if err:
            return err
        # SECURITY: don't hand a club's full record (incl. the club_token shell-linking
        # secret and owner contacts) to non-members. Was readable by any authenticated
        # user via id enumeration. Require owner / active member / platform admin.
        u = request.user
        is_admin = getattr(u, "user_type", "") == "admin" or getattr(u, "is_superuser", False)
        if not is_admin and club.owner_id != u.pk:
            from apps.clubs.models import ClubMembership
            if not ClubMembership.objects.filter(user=u, club_id=pk, is_active=True).exists():
                return Response({"error": "Нет доступа к клубу"}, status=status.HTTP_403_FORBIDDEN)
        return Response(ClubSerializer(club).data)

    def patch(self, request, pk):
        club, err = self._get_club(pk, request.user)
        if err:
            return err
        # Only owner or platform admin can update
        is_owner = club.owner_id == request.user.pk
        is_admin = getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False)
        if not (is_owner or is_admin):
            return Response({"error": "Нет прав на редактирование клуба"}, status=status.HTTP_403_FORBIDDEN)
        serializer = ClubUpdateSerializer(club, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ClubSerializer(club).data)


@extend_schema(tags=["Clubs"])
class ClubSettingsAPIView(APIView):
    """GET/PATCH operational settings for a club.

    GET  /api/v1/clubs/<pk>/settings/ → returns { data: {...} }
    PATCH /api/v1/clubs/<pk>/settings/ → merges provided keys into data, returns updated { data: {...} }
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_club(self, pk, request):
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return None, Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        # Settings hold sensitive data (Telegram token etc.) — owner/member/admin only.
        is_owner = club.owner_id == request.user.pk
        is_admin = getattr(request.user, "user_type", "") == "admin"
        is_member = ClubMembership.objects.filter(user=request.user, club=club, is_active=True).exists()
        if not (is_owner or is_admin or is_member):
            return None, Response({"error": "Нет доступа к настройкам этого клуба"}, status=status.HTTP_403_FORBIDDEN)
        return club, None

    def get(self, request, pk):
        club, err = self._get_club(pk, request)
        if err:
            return err
        obj, _ = ClubSettings.objects.get_or_create(club=club)
        return Response({"data": obj.data})

    def patch(self, request, pk):
        club, err = self._get_club(pk, request)
        if err:
            return err
        # SECURITY: settings carry sensitive keys (telegram_bot_token, dadata_api_key,
        # payment-cancel gates). GET is fine for any member, but WRITES must be
        # owner/manager/admin only — an operator must not rewire bot tokens / gates.
        is_owner = club.owner_id == request.user.pk
        is_admin = getattr(request.user, "user_type", "") == "admin"
        is_manager = ClubMembership.objects.filter(
            user=request.user, club=club, is_active=True, role__in=["owner", "manager"]
        ).exists()
        if not (is_owner or is_admin or is_manager):
            return Response({"error": "Только владелец или менеджер может менять настройки"},
                            status=status.HTTP_403_FORBIDDEN)
        obj, _ = ClubSettings.objects.get_or_create(club=club)
        incoming = request.data.get("data", request.data)
        if isinstance(incoming, dict):
            obj.data = {**obj.data, **incoming}
            obj.save(update_fields=["data", "updated_at"])
            # If any branding key changed, push the new theme to online shells so
            # they recolor on the fly (no re-login / restart).
            if any(k in incoming for k in ClubBrandingAPIView.BRANDING_KEYS):
                _broadcast_branding(club.pk, obj.data)
        return Response({"data": obj.data})


@extend_schema(tags=["Clubs"])
class ClubDadataLookupAPIView(APIView):
    """GET /api/v1/clubs/<pk>/dadata/party/?inn=... — server-side proxy to DaData's
    findById/party. The browser can't call DaData directly (CORS); this uses the
    club's saved `dadata_api_key` server-side and returns the org details."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        inn = (request.query_params.get("inn") or "").strip()
        if not inn.isdigit() or len(inn) not in (10, 12):
            return Response({"error": "ИНН должен быть 10 или 12 цифр"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        # Uses the club's PAID DaData key → restrict to owner/manager/admin (not
        # any member/operator, who could burn quota / harvest org data).
        is_owner = club.owner_id == request.user.pk
        is_admin = getattr(request.user, "user_type", "") == "admin"
        is_manager = ClubMembership.objects.filter(
            user=request.user, club=club, is_active=True, role__in=["owner", "manager"]
        ).exists()
        if not (is_owner or is_admin or is_manager):
            return Response({"error": "Нет доступа"}, status=status.HTTP_403_FORBIDDEN)

        obj, _ = ClubSettings.objects.get_or_create(club=club)
        key = (obj.data or {}).get("dadata_api_key", "")
        if not key:
            return Response({"error": "Не указан API-ключ DaData (Интеграции)"}, status=status.HTTP_400_BAD_REQUEST)

        import json as _json
        import urllib.request as _req
        try:
            r = _req.Request(
                "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party",
                data=_json.dumps({"query": inn}).encode(),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Token {key}", "Accept": "application/json"},
                method="POST",
            )
            with _req.urlopen(r, timeout=10) as resp:
                data = _json.loads(resp.read())
        except Exception:
            # Don't reflect the upstream exception (could carry request/key context).
            return Response({"error": "DaData временно недоступна"}, status=status.HTTP_502_BAD_GATEWAY)

        sug = data.get("suggestions") or []
        if not sug:
            return Response({"found": False})
        d = sug[0].get("data", {}) or {}
        return Response({
            "found": True,
            "legal_name": (d.get("name") or {}).get("full_with_opf") or sug[0].get("value", ""),
            "legal_address": (d.get("address") or {}).get("value", ""),
            "ogrn": d.get("ogrn", ""),
        })


@extend_schema(tags=["Clubs"])
class ClubBrandingAPIView(APIView):
    """GET /api/v1/clubs/<pk>/branding/ — PUBLIC, non-sensitive theme only.

    The C# shell needs the club's background/logo/colors BEFORE a user logs in
    (login screen branding) and for client users who are not club members. The
    full /settings/ endpoint is owner/member-gated and holds secrets (Telegram
    tokens), so branding is split out here as a safe, auth-free whitelist.
    """

    permission_classes = [permissions.AllowAny]
    throttle_scope = "pc_register"

    # Only visual, non-sensitive keys are ever exposed.
    BRANDING_KEYS = BRANDING_KEYS

    def get(self, request, pk):
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        obj, _ = ClubSettings.objects.get_or_create(club=club)
        data = obj.data or {}
        branding = {k: data[k] for k in self.BRANDING_KEYS if k in data}
        return Response({"data": branding})


@extend_schema(tags=["Clubs"])
class ClubBrandingUploadAPIView(APIView):
    """POST /api/v1/clubs/<pk>/settings/branding/ — upload a club logo or shell
    background image.

    multipart/form-data: file=<image>, kind=logo|background
    Saves the file under MEDIA_ROOT/clubs/<kind>/<club_id>/, stores the absolute
    URL in ClubSettings.data ('logo_url' / 'shell_background_url' — the exact keys
    the C# shell reads), and returns { url, key, data }.
    """

    permission_classes = [permissions.IsAuthenticated]

    MAX_BYTES = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
    KIND_TO_KEY = {"logo": "logo_url", "background": "shell_background_url"}

    def _get_club(self, pk, request):
        # Same owner/member/admin gate as the settings endpoint.
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return None, Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        is_owner = club.owner_id == request.user.pk
        is_admin = getattr(request.user, "user_type", "") == "admin"
        is_member = ClubMembership.objects.filter(user=request.user, club=club, is_active=True).exists()
        if not (is_owner or is_admin or is_member):
            return None, Response({"error": "Нет доступа к настройкам этого клуба"}, status=status.HTTP_403_FORBIDDEN)
        return club, None

    def post(self, request, pk):
        import os
        from django.conf import settings as dj_settings
        from django.core.files.storage import default_storage

        club, err = self._get_club(pk, request)
        if err:
            return err

        kind = (request.data.get("kind") or "").strip().lower()
        if kind not in self.KIND_TO_KEY:
            return Response({"error": "kind должен быть 'logo' или 'background'"}, status=status.HTTP_400_BAD_REQUEST)

        upload = request.FILES.get("file")
        if not upload:
            return Response({"error": "Файл не передан (поле 'file')"}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > self.MAX_BYTES:
            return Response({"error": "Файл больше 5 МБ"}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in self.ALLOWED_EXT:
            return Response(
                {"error": f"Недопустимый формат. Разрешено: {', '.join(sorted(self.ALLOWED_EXT))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Stable filename per kind/club so re-uploads overwrite the previous file
        # (no orphaned media accumulating).
        rel_path = f"clubs/{kind}/{club.pk}/{kind}{ext}"
        if default_storage.exists(rel_path):
            default_storage.delete(rel_path)
        saved_path = default_storage.save(rel_path, upload)

        media_url = dj_settings.MEDIA_URL.rstrip("/") + "/" + saved_path.lstrip("/")
        absolute_url = request.build_absolute_uri(media_url)

        key = self.KIND_TO_KEY[kind]
        obj, _ = ClubSettings.objects.get_or_create(club=club)
        obj.data = {**obj.data, key: absolute_url}
        obj.save(update_fields=["data", "updated_at"])

        # Live push: shells in this club swap the logo/background on the fly.
        _broadcast_branding(club.pk, obj.data)

        return Response({"url": absolute_url, "key": key, "data": obj.data}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Clubs"])
class ClubPromisedPaymentAPIView(APIView):
    """POST /api/v1/clubs/<pk>/promised-payment/ — activate a 7-day promised payment.

    Available to the club OWNER (or platform admin). Extends the subscription by
    7 days, marks status PROMISED, and records a 500сум debt due in 37 days.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from django.utils import timezone
        from decimal import Decimal
        from apps.clubs.models import ClubSubscription, PromisedPayment, SubscriptionPlan

        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)

        is_owner = club.owner_id == request.user.pk
        is_admin = getattr(request.user, "user_type", "") == "admin"
        if not (is_owner or is_admin):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        sub, _ = ClubSubscription.objects.get_or_create(
            club=club,
            defaults={"plan": SubscriptionPlan.objects.filter(tier="free").first()},
        )

        # Already has an active (unpaid) promised payment?
        existing = PromisedPayment.objects.filter(subscription=sub, paid_at__isnull=True).first()
        if existing:
            return Response({"error": "Обещанный платёж уже активен"}, status=status.HTTP_400_BAD_REQUEST)

        # Extend subscription 7 days, set PROMISED, create debt due in 37 days
        new_expires = (sub.expires_at or now) + timezone.timedelta(days=7) if (sub.expires_at and sub.expires_at > now) else now + timezone.timedelta(days=7)
        sub.expires_at = new_expires
        sub.status = SubscriptionStatus.PROMISED
        sub.save(update_fields=["expires_at", "status"])

        club.trial_until = new_expires
        club.save(update_fields=["trial_until"])

        pp = PromisedPayment.objects.create(
            subscription=sub,
            fee_amount=Decimal("500"),
            due_at=now + timezone.timedelta(days=37),
        )

        return Response({
            "success": True,
            "message": "Обещанный платёж подключён. Подписка продлена на 7 дней.",
            "fee": str(pp.fee_amount),
            "due_at": pp.due_at.isoformat(),
            "extended_until": new_expires.isoformat(),
        })

    def delete(self, request, pk):
        """Pay off the promised payment debt (mark paid)."""
        from django.utils import timezone
        from apps.clubs.models import PromisedPayment, ClubSubscription, SubscriptionStatus

        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)

        is_owner = club.owner_id == request.user.pk
        is_admin = getattr(request.user, "user_type", "") == "admin"
        if not (is_owner or is_admin):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        try:
            sub = club.subscription
        except ClubSubscription.DoesNotExist:
            return Response({"error": "Нет подписки"}, status=status.HTTP_404_NOT_FOUND)

        pp = PromisedPayment.objects.filter(subscription=sub, paid_at__isnull=True).first()
        if not pp:
            return Response({"error": "Нет активного обещанного платежа"}, status=status.HTTP_400_BAD_REQUEST)
        pp.paid_at = timezone.now()
        pp.save(update_fields=["paid_at"])
        if sub.status == SubscriptionStatus.PROMISED:
            sub.status = SubscriptionStatus.ACTIVE
            sub.save(update_fields=["status"])
        return Response({"success": True, "message": "Долг по обещанному платежу погашен"})


@extend_schema(tags=["Clubs"])
class ClubTelegramTestAPIView(APIView):
    """POST /api/v1/clubs/<pk>/telegram/test/ — send a test message to the configured channel."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # Accept token/chat_id from request body (for testing before saving)
        # or fall back to saved ClubSettings
        token   = (request.data.get("bot_token")  or "").strip()
        chat_id = (request.data.get("chat_id")    or "").strip()

        if token and chat_id:
            # Test with provided values directly (no DB read needed)
            from apps.clubs.services.telegram import notify_club as _send
            import urllib.request, json as _json
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = _json.dumps({
                "chat_id": chat_id,
                "text": "✅ <b>PCHub</b> — тестовое сообщение. Интеграция работает!",
                "parse_mode": "HTML",
            }).encode("utf-8")
            try:
                req = urllib.request.Request(url, data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    result = _json.loads(resp.read())
                if result.get("ok"):
                    return Response({"success": True, "message": "Сообщение отправлено в Telegram ✅"})
                desc = result.get("description", "Ошибка Telegram API")
                return Response({"success": False, "error": desc}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"success": False, "error": f"Нет связи: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Fall back to saved settings
            from apps.clubs.services.telegram import test_notify
            ok, error = test_notify(pk)
            if ok:
                return Response({"success": True, "message": "Сообщение отправлено в Telegram ✅"})
            return Response({"success": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Clubs"])
class ClubTokenRegenerateAPIView(APIView):
    """POST /api/v1/clubs/<pk>/regenerate-token/ — owner/admin only."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)

        is_owner = club.owner_id == request.user.pk
        is_admin = getattr(request.user, "user_type", "") == "admin"
        if not (is_owner or is_admin):
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)

        from apps.clubs.models.club import _generate_club_token
        token = _generate_club_token()
        while Club.objects.filter(club_token=token).exclude(pk=pk).exists():
            token = _generate_club_token()

        club.club_token = token
        club.save(update_fields=["club_token"])
        return Response({"club_token": club.club_token})


@extend_schema(tags=["Clubs"])
class ClubTokenVerifyAPIView(APIView):
    """GET /api/v1/clubs/verify-token/?token=XXXXXXXX
    Public endpoint — shell calls this BEFORE saving the token to validate it.
    Returns club name on success, 404 on invalid token.
    """
    permission_classes = []  # no auth required — called before login
    throttle_scope = "pc_register"  # rate-limit token brute-force

    def get(self, request):
        token = (request.query_params.get("token") or "").strip().upper()
        if not token:
            return Response({"error": "token обязателен"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            club = Club.objects.get(club_token=token, is_active=True)
        except Club.DoesNotExist:
            return Response(
                {"error": f"Клуб с токеном «{token}» не найден. Проверьте токен в настройках клуба."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"id": club.id, "name": club.name, "city": club.city or ""})


@extend_schema(tags=["Clubs"])
class ClubSubscriptionAPIView(APIView):
    """GET subscription status for a club.

    Returns trial days left, current status, plan info.
    PATCH (platform admin only): extend trial, change status/plan.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _subscription_data(self, club):
        from django.utils import timezone

        now = timezone.now()
        trial_days_left = None
        if club.trial_until:
            diff = (club.trial_until - now).total_seconds() / 86400
            trial_days_left = max(0, int(diff))

        try:
            sub = club.subscription
            sub_status = sub.status
            plan_name = sub.plan.name if sub.plan else "Free"
            plan_tier = sub.plan.tier if sub.plan else "free"
            expires_at = sub.expires_at
        except ClubSubscription.DoesNotExist:
            sub = None
            sub_status = SubscriptionStatus.TRIAL if club.is_trial else SubscriptionStatus.ACTIVE
            plan_name = "Free"
            plan_tier = "free"
            expires_at = club.trial_until

        # Auto-expire trial
        if sub_status == SubscriptionStatus.TRIAL and club.trial_until and now > club.trial_until:
            sub_status = SubscriptionStatus.EXPIRED

        is_blocked = sub_status in (SubscriptionStatus.EXPIRED, SubscriptionStatus.BLOCKED)

        # ── Promised payment info ──────────────────────────────────────────
        promised = None
        try:
            from apps.clubs.models import PromisedPayment
            if sub:
                pp = (
                    PromisedPayment.objects.filter(subscription=sub, paid_at__isnull=True)
                    .order_by("-granted_at").first()
                )
                if pp:
                    days_to_pay = max(0, int((pp.due_at - now).total_seconds() / 86400))
                    promised = {
                        "active": True,
                        "fee": str(pp.fee_amount),
                        "granted_at": pp.granted_at.isoformat(),
                        "due_at": pp.due_at.isoformat(),
                        "days_to_pay": days_to_pay,
                        "overdue": now > pp.due_at,
                    }
        except Exception:
            pass

        return {
            "status": sub_status,
            "is_trial": club.is_trial,
            "is_blocked": is_blocked,
            "trial_until": club.trial_until.isoformat() if club.trial_until else None,
            "trial_days_left": trial_days_left,
            "plan": plan_name,
            "plan_tier": plan_tier,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "promised_payment": promised,
            "panel_version": "9.0.0",
            "club_id": club.id,
        }

    def get(self, request, pk):
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        # Only the club owner, an active member, or a platform admin may read.
        is_owner = club.owner_id == request.user.pk
        is_admin = getattr(request.user, "user_type", "") == "admin"
        is_member = ClubMembership.objects.filter(
            user=request.user, club=club, is_active=True
        ).exists()
        if not (is_owner or is_admin or is_member):
            return Response({"error": "Нет доступа к этому клубу"}, status=status.HTTP_403_FORBIDDEN)
        return Response(self._subscription_data(club))

    def patch(self, request, pk):
        """Platform admin: extend trial or change subscription status."""
        if getattr(request.user, "user_type", "") != "admin":
            return Response({"error": "Только платформ-администратор"}, status=status.HTTP_403_FORBIDDEN)

        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)

        from django.utils import timezone
        from apps.clubs.models import SubscriptionPlan

        action = request.data.get("action")

        def _safe_days(raw, default):
            try:
                return max(1, min(3650, int(raw)))
            except (TypeError, ValueError):
                return default

        if action == "extend_trial":
            days = _safe_days(request.data.get("days", 14), 14)
            new_until = timezone.now() + timezone.timedelta(days=days)
            club.trial_until = new_until
            club.is_trial = True
            club.save(update_fields=["trial_until", "is_trial"])
            try:
                sub, _ = ClubSubscription.objects.get_or_create(
                    club=club,
                    defaults={"plan": SubscriptionPlan.objects.filter(tier="free").first()},
                )
                sub.status = SubscriptionStatus.TRIAL
                sub.expires_at = new_until
                sub.save(update_fields=["status", "expires_at"])
            except Exception:
                pass

        elif action == "activate":
            tier = request.data.get("tier", "starter")
            days = _safe_days(request.data.get("days", 30), 30)
            expires = timezone.now() + timezone.timedelta(days=days)
            plan = SubscriptionPlan.objects.filter(tier=tier).first()
            if not plan:
                return Response({"error": f"Тариф «{tier}» не найден"}, status=status.HTTP_400_BAD_REQUEST)
            sub, _ = ClubSubscription.objects.get_or_create(club=club, defaults={"plan": plan})
            sub.plan = plan
            sub.status = SubscriptionStatus.ACTIVE
            sub.expires_at = expires
            sub.save(update_fields=["plan", "status", "expires_at"])
            club.is_trial = False
            club.save(update_fields=["is_trial"])

        elif action == "block":
            sub, _ = ClubSubscription.objects.get_or_create(
                club=club, defaults={"plan": SubscriptionPlan.objects.filter(tier="free").first()})
            sub.status = SubscriptionStatus.BLOCKED
            sub.save(update_fields=["status"])

        else:
            return Response({"error": "Неизвестное действие. Используй: extend_trial, activate, block"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self._subscription_data(club))

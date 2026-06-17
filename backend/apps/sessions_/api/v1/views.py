from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.clubs.api.v1.mixins import TenantFilterMixin
from apps.sessions_.api.v1.serializers import (
    AdminCallSerializer,
    ClientSessionSerializer,
    ReviewSerializer,
)
from apps.sessions_.models import AdminCall, ClientSession, Review


def _is_club_staff(user, club_id):
    """Operator/manager/owner/platform-admin of the club — marking reviews read and
    answering admin-calls are STAFF actions; was open to any authenticated client."""
    if not club_id:
        return False
    if getattr(user, "user_type", "") == "admin":
        return True
    try:
        from apps.clubs.models import Club, ClubMembership
        if Club.objects.filter(id=club_id, owner=user).exists():
            return True
        return ClubMembership.objects.filter(
            user=user, club_id=club_id, is_active=True,
            role__in=["owner", "manager", "operator"],
        ).exists()
    except Exception:
        return False


class ClientSessionListAPIView(TenantFilterMixin, generics.ListAPIView):
    serializer_class = ClientSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ClientSession.objects.all().prefetch_related("hosts").select_related("client", "tariff")

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class ClientSessionDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateAPIView):
    """Tenant-scoped — was ClientSession.objects.all() with no club filter, so any
    operator could GET/PATCH another club's session by id (IDOR + PII leak)."""
    serializer_class = ClientSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ClientSession.objects.all()

    def update(self, request, *args, **kwargs):
        # Editing a session (status/duration/etc.) is a STAFF action — was open to any
        # authenticated member regardless of role.
        obj = self.get_object()
        if not _is_club_staff(request.user, obj.club_id):
            return Response({"detail": "Только для персонала клуба"}, status=status.HTTP_403_FORBIDDEN)
        resp = super().update(request, *args, **kwargs)
        # Stamp the terminal timestamps — a PATCH to status=finished/cancelled left
        # finished_at/cancelled_at NULL (broken «когда завершилась» reporting).
        from django.utils import timezone
        obj.refresh_from_db()
        fields = []
        if obj.status == "finished" and obj.finished_at is None:
            obj.finished_at = timezone.now(); fields.append("finished_at")
        if obj.status == "cancelled" and obj.cancelled_at is None:
            obj.cancelled_at = timezone.now(); fields.append("cancelled_at")
        if fields:
            obj.save(update_fields=fields)
        return resp


class ReviewListAPIView(TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Review.objects.all().select_related("client", "computer", "session")

    def get_queryset(self):
        # ?is_read filter was ignored (no unread view). Apply on top of tenant scope.
        qs = super().get_queryset()
        r = (self.request.query_params.get("is_read") or "").lower()
        if r in ("1", "true"):
            qs = qs.filter(is_read=True)
        elif r in ("0", "false"):
            qs = qs.filter(is_read=False)
        return qs

    def perform_create(self, serializer):
        # The client never supplies their own identity or club — derive them
        # server-side from the authenticated user and resolved tenant.
        from rest_framework.exceptions import ValidationError
        club_id = getattr(self.request, "current_club_id", None) or self.request.data.get("club")
        if not club_id:
            # club is NOT NULL — without a resolved club this 500'd on IntegrityError.
            raise ValidationError({"club": "Не удалось определить клуб (укажите ?club=)"})
        serializer.save(client=self.request.user, club_id=club_id)


class ReviewMarkReadAPIView(TenantFilterMixin, generics.UpdateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Review.objects.all()

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not _is_club_staff(request.user, obj.club_id):
            return Response({"detail": "Только для персонала клуба"}, status=status.HTTP_403_FORBIDDEN)
        obj.is_read = True
        obj.save(update_fields=["is_read"])
        return Response(self.get_serializer(obj).data)


class AdminCallListCreateAPIView(TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = AdminCallSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = AdminCall.objects.all().select_related("computer", "client")

    def get_queryset(self):
        # ?is_answered filter was ignored (no unanswered queue view).
        qs = super().get_queryset()
        a = (self.request.query_params.get("is_answered") or "").lower()
        if a in ("1", "true"):
            qs = qs.filter(answered_at__isnull=False)
        elif a in ("0", "false"):
            qs = qs.filter(answered_at__isnull=True)
        return qs

    def perform_create(self, serializer):
        # A client calling the operator is always themselves, in the current club.
        # computer may be supplied by the shell (it knows its own DB id) or left null.
        from rest_framework.exceptions import ValidationError
        club_id = getattr(self.request, "current_club_id", None) or self.request.data.get("club")
        if not club_id:
            raise ValidationError({"club": "Не удалось определить клуб (укажите ?club=)"})
        serializer.save(client=self.request.user, club_id=club_id)


class AdminCallAnswerAPIView(TenantFilterMixin, generics.UpdateAPIView):
    serializer_class = AdminCallSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = AdminCall.objects.all()

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not _is_club_staff(request.user, obj.club_id):
            return Response({"detail": "Только для персонала клуба"}, status=status.HTTP_403_FORBIDDEN)
        if not obj.answered_at:
            obj.answered_at = timezone.now()
            obj.answered_by = request.user
            obj.save(update_fields=["answered_at", "answered_by"])
        return Response(self.get_serializer(obj).data)

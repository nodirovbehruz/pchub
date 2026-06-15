"""Tenant isolation middleware for PCHub.

Reads `X-Club-Id` HTTP header (or `?club=` query param as fallback) and
attaches `request.current_club_id` plus `request.current_club` to the request.

Validates that the authenticated user is either:
  - owner of the club, OR
  - platform admin (is_superuser / user_type=admin), OR
  - active member via ClubMembership.

The middleware **does not block** the request when the header is missing —
that's the responsibility of individual views/resolvers (they should check
`request.current_club_id` and reject anonymous-tenant operations as needed).

This keeps simple things simple (login, listing my-clubs, registering a new
client without a club context) while enabling strict isolation per-resource.
"""

from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin


HEADER_NAME = "HTTP_X_CLUB_ID"
QUERY_PARAM = "club"


class ClubTenantMiddleware(MiddlewareMixin):
    """Resolve the current club for the request and attach to the request object."""

    def process_request(self, request):
        request.current_club_id = None
        request.current_club = None
        request.current_membership_role = None

        club_id = request.META.get(HEADER_NAME) or request.GET.get(QUERY_PARAM)
        if not club_id:
            return None

        try:
            club_id = int(club_id)
        except (TypeError, ValueError):
            return None

        # Lazy import to avoid AppRegistryNotReady during startup.
        from apps.clubs.models import Club, ClubMembership

        try:
            club = Club.objects.only("id", "name", "is_active", "owner_id").get(id=club_id)
        except Club.DoesNotExist:
            return None

        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            # Anonymous request — keep ids visible but role unknown
            request.current_club_id = club.id
            request.current_club = club
            return None

        # Only PLATFORM admins (user_type='admin') bypass ownership check.
        # Club owners have is_superuser=True but should NOT access other clubs.
        is_platform_admin = getattr(user, "user_type", "") == "admin"

        if is_platform_admin:
            request.current_club_id = club.id
            request.current_club = club
            request.current_membership_role = "platform_admin"
            return None

        if club.owner_id == user.id:
            request.current_club_id = club.id
            request.current_club = club
            request.current_membership_role = "owner"
            return None

        membership = (
            ClubMembership.objects
            .filter(user=user, club=club, is_active=True)
            .values_list("role", flat=True)
            .first()
        )
        if membership:
            request.current_club_id = club.id
            request.current_club = club
            request.current_membership_role = membership
            return None

        # User is not allowed in this club — leave current_club_id as None
        # so QuerySets default to empty.
        return None


class SubscriptionGateMiddleware(MiddlewareMixin):
    """B2B gate: a club whose platform subscription is inactive can't perform
    management WRITES. Triggered by the MANAGEMENT ROLE of the request (owner /
    manager / operator), NOT by the presence of the X-Club-Id header — so it can't
    be bypassed by addressing the tenant via ?club=. The kiosk shell authenticates
    as a guest/client (no management role) and is therefore never gated.

    Platform admins always pass. A small set of self-service billing/recovery
    endpoints stay reachable while blocked so the owner can pay and restore access.
    """

    # Exact path SUFFIXES that must stay reachable even when blocked. Anchored to
    # the trailing segments (not loose substrings) to avoid accidental matches like
    # "/token" matching "/regenerate-token/".
    WHITELIST_SUFFIXES = (
        "/wallet/", "/wallet/topup/",            # balance view + super-admin top-up
        "/subscription/", "/subscription/buy/",  # status + pay/renew
        "/subscription/grant/", "/promised-payment/",  # recovery mechanisms
        "/plans/",                                # plan list
    )
    # Substrings allowed anywhere (auth + branding the shell/login need pre-gate).
    WHITELIST_CONTAINS = ("/accounts/login", "/accounts/profile", "/auth/", "/branding/")

    MANAGEMENT_ROLES = ("owner", "manager", "operator")

    def _authed_user(self, request):
        """request.user is AnonymousUser in middleware for JWT requests (DRF auths
        in the view), so decode the Bearer token here to get the real user."""
        u = getattr(request, "user", None)
        if u is not None and getattr(u, "is_authenticated", False):
            return u
        auth = request.META.get("HTTP_AUTHORIZATION", "") or ""
        if not auth.lower().startswith("bearer "):
            return None
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth import get_user_model
            acc = AccessToken(auth[7:])
            return get_user_model().objects.filter(pk=acc["user_id"]).first()
        except Exception:
            return None

    def process_request(self, request):
        club = getattr(request, "current_club", None)
        if club is None:
            return None
        # Reads stay allowed (panel still loads to show the "pay" screen).
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        path = request.path or ""
        if path.endswith(self.WHITELIST_SUFFIXES) or any(f in path for f in self.WHITELIST_CONTAINS):
            return None

        user = self._authed_user(request)
        if user is None:
            return None  # unauthenticated → let the view reject it
        # Platform admins are never gated.
        if getattr(user, "user_type", "") == "admin" or getattr(user, "is_admin", False):
            return None
        # Gate only club MANAGEMENT (owner/manager/operator). Shell logs in as a
        # guest/client → not a management role → never gated, regardless of ?club=.
        from apps.clubs.models import ClubMembership
        is_mgmt = (club.owner_id == user.pk) or ClubMembership.objects.filter(
            user=user, club=club, is_active=True, role__in=self.MANAGEMENT_ROLES,
        ).exists()
        if not is_mgmt:
            return None

        from apps.clubs.services import billing as billing_service
        if billing_service.subscription_active(club):
            return None

        from django.http import JsonResponse
        return JsonResponse(
            {"error": "Подписка клуба неактивна. Оплатите тариф, чтобы продолжить.",
             "code": "subscription_inactive"},
            status=402,
        )

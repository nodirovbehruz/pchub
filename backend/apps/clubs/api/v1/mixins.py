"""Common DRF mixins for tenant isolation and shared filters."""

from rest_framework import permissions


def validated_club_id(request):
    """The club id the AUTHENTICATED user is actually authorized for (owner / active
    member / platform admin), else None.

    SECURITY: request.current_club_id is set by ClubTenantMiddleware from
    ?club=/X-Club-Id BEFORE DRF authenticates the JWT (request.user is anonymous in
    middleware), so it is attacker-controllable and must NOT be trusted on its own.
    In the DRF view request.user IS authenticated, so we re-check membership here.
    NOTE: club owners carry is_superuser=True, so we must NOT use is_superuser as a
    bypass — only user_type=='admin' (real platform admin) bypasses.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    cid = getattr(request, "current_club_id", None)
    if not cid:
        cid = request.query_params.get("club") if hasattr(request, "query_params") else request.GET.get("club")
    if not cid:
        return None
    try:
        cid = int(cid)
    except (TypeError, ValueError):
        return None
    if getattr(user, "user_type", "") == "admin":
        return cid
    from apps.clubs.models import Club, ClubMembership
    if Club.objects.filter(id=cid, owner=user).exists():
        return cid
    if ClubMembership.objects.filter(user=user, club_id=cid, is_active=True).exists():
        return cid
    return None


class TenantFilterMixin:
    """Filter queryset by the club the user is AUTHORIZED for (tenant isolation)."""

    tenant_field = "club_id"

    def filter_by_tenant(self, qs):
        club_id = validated_club_id(self.request)
        if club_id:
            return qs.filter(**{self.tenant_field: club_id})
        return qs.none()  # no authorized club → no rows (was leaking via raw ?club=)

    def get_queryset(self):
        qs = super().get_queryset()
        return self.filter_by_tenant(qs)


class TenantCreateMixin:
    """WRITE-side tenant isolation for ListCreate views. TenantFilterMixin only
    scopes reads — on CREATE the serializer's `club` field (or current_club_id) is
    attacker-controllable, so force the new object's club to the AUTHORIZED tenant.
    Views needing extra create fields (created_by/admin) override `tenant_create_extra`.
    """

    def tenant_create_extra(self):
        return {}

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        cid = validated_club_id(self.request)
        if not cid:
            raise PermissionDenied("Нет доступа к клубу")
        # Drop any body-supplied club so it can't override the authorized one.
        try:
            serializer.validated_data.pop("club", None)
        except Exception:
            pass
        serializer.save(club_id=cid, **self.tenant_create_extra())


class IsAuthenticatedTenant(permissions.IsAuthenticated):
    """Authenticated user with a club they are actually authorized for."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if getattr(request.user, "user_type", "") == "admin":
            return True
        return validated_club_id(request) is not None

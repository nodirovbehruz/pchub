from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Read-only access to anyone.
    Write access for the platform admin AND the club's own staff (owner/manager/operator)
    — they must be able to manage their shop catalog (categories/products/stock). Clients
    are NOT club members, so they can't write.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        if not (user and user.is_authenticated):
            return False
        # Platform admin can write anything.
        if getattr(user, "is_admin", False):
            return True
        # Club staff: validated_club_id is non-None only for the club's owner/member
        # (or platform admin) — never for a plain client. Lets owners manage their shop.
        from apps.clubs.api.v1.mixins import validated_club_id
        return validated_club_id(request) is not None

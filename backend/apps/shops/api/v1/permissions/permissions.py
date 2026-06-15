from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to anyone
    Write access only for admins
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for admin users
        return request.user and request.user.is_authenticated and request.user.is_admin

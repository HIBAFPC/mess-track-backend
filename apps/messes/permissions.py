from rest_framework import permissions

from apps.accounts.models import User

ALLOWED_MESS_MANAGEMENT_ROLES = (
    User.Role.SUPER_ADMIN,
    User.Role.MESS_ADMIN,
)


class IsMessManager(permissions.BasePermission):
    """Allows access only to active super admins and mess admins."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role in ALLOWED_MESS_MANAGEMENT_ROLES
        )


class IsMessOwnerOrSuperAdmin(permissions.BasePermission):
    """Allows object access to a mess owner or any super admin."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (
                user.role == User.Role.SUPER_ADMIN
                or getattr(obj, "owner_id", None) == user.id
            )
        )


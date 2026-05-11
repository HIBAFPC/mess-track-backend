from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to super admin users.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_super_admin
        )


class IsMessAdmin(permissions.BasePermission):
    """
    Allows access only to mess admin users.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_mess_admin
        )


class IsResident(permissions.BasePermission):
    """
    Allows access only to resident users.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_resident
        )


class IsAuthenticatedAndActive(permissions.BasePermission):
    """
    Allows access only to authenticated and active users.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )

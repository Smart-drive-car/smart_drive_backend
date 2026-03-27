from rest_framework import permissions
from .models import Role


class IsDriver(permissions.BasePermission):
    """
    Permission to check if the user is a Driver.
    """
    message = "You do not have permission to perform this action. Driver role required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'role', None) == Role.DRIVER)


class IsWorkshop(permissions.BasePermission):
    """
    Permission to check if the user is a Workshop.
    """
    message = "You do not have permission to perform this action. Workshop role required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'role', None) == Role.WORKSHOP)




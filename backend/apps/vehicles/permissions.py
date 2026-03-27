from rest_framework import permissions
from rest_framework.permissions import BasePermission
from apps.users.models import Role

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # SAFE_METHODS are GET, HEAD, or OPTIONS. These are always allowed.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the item.
        if hasattr(obj, 'owner') and hasattr(obj.owner, 'user'):
            return obj.owner.user == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return False


# apps/vehicles/permissions.py



class IsWorkshopOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in [Role.WORKSHOP, Role.ADMIN]
        )

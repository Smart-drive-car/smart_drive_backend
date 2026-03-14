from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # SAFE_METHODS are GET, HEAD, or OPTIONS. These are always allowed.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the item.
        return obj.user == request.user
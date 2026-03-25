from rest_framework import permissions


class IsOwnDriverProfile(permissions.BasePermission):
    message = "You do not have permission to modify this profile."

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

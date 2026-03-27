from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsWorkshopOrReadOnly(BasePermission):
    """
    DRIVER → faqat GET
    WORKSHOP → CRUD
    ADMIN → CRUD
    """

    def has_permission(self, request, view):
        user = request.user

        if user.role == 'DRIVER':
            return request.method in SAFE_METHODS

        if user.role in ['WORKSHOP', 'ADMIN']:
            return True

        return False


class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'ADMIN'


class IsAdminOrWorkshopReadOnly(BasePermission):
    """
    ADMIN -> CRUD
    WORKSHOP -> GET only
    DRIVER -> No access
    """
    def has_permission(self, request, view):
        user = request.user
        if user.role == 'ADMIN':
            return True
        if user.role == 'WORKSHOP' and request.method in SAFE_METHODS:
            return True
        return False


class IsServiceTypeOwnerOrAdmin(BasePermission):
    """
    Admin can do anything.
    Workshop can only modify/delete their own ServiceType (where owner=workshopprofile).
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == "ADMIN":
            return True

        if user.role == "WORKSHOP":
            if request.method in SAFE_METHODS:
                return obj.owner is None or obj.owner == user.workshopprofile
            return obj.owner == user.workshopprofile

        return False
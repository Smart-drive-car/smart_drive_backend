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
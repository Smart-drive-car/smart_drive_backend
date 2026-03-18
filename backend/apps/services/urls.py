from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceTypeViewSet, ServiceViewSet

router = DefaultRouter()
router.register(r'service-types', ServiceTypeViewSet)
router.register(r'services', ServiceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
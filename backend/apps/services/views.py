from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import ServiceType, Service
from .serializers import ServiceTypeSerializer, ServiceSerializer
from .permissions import IsWorkshopOrReadOnly, IsAdminOnly


# 🔹 ServiceType → faqat ADMIN
class ServiceTypeViewSet(viewsets.ModelViewSet):
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminOnly]


# 🔹 Service → asosiy logic
class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated, IsWorkshopOrReadOnly]

    def get_queryset(self):
        user = self.request.user

        # 🛠 Workshop → faqat o'z service
        if user.role == 'WORKSHOP':
            return Service.objects.filter(workshop=user.workshopprofile)

        # 🚗 Driver → faqat o'z mashinalariga tegishli service
        if user.role == 'DRIVER':
            return Service.objects.filter(
                car__drivercar__driver_profile=user.driverprofile
            )

        # 👑 Admin → hammasi
        if user.role == 'ADMIN':
            return Service.objects.all()

        return Service.objects.none()

    def perform_create(self, serializer):
        user = self.request.user

        if user.role != 'WORKSHOP':
            raise PermissionDenied("Only workshop can create service")

        serializer.save(workshop=user.workshopprofile)

    def perform_update(self, serializer):
        service = self.get_object()
        user = self.request.user

        if user.role == 'WORKSHOP':
            if service.workshop != user.workshopprofile:
                raise PermissionDenied("You can update only your services")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if user.role == 'WORKSHOP':
            if instance.workshop != user.workshopprofile:
                raise PermissionDenied("You can delete only your services")

        instance.delete()
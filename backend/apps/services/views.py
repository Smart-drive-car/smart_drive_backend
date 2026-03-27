from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
import logging
from django.db import models

from .models import ServiceType, Service
from .serializers import ServiceTypeSerializer, ServiceSerializer
from apps.users.models import UserDeviceToken
from apps.shared.push_notifications import send_push_to_tokens
from apps.vehicles.models import DriverCar


logger = logging.getLogger(__name__)
from .permissions import IsWorkshopOrReadOnly, IsAdminOnly, IsServiceTypeOwnerOrAdmin, IsAdminOrWorkshopReadOnly


# 🔹 ServiceType → ADMIN (global) + WORKSHOP (o'ziga tegishli)
class ServiceTypeViewSet(viewsets.ModelViewSet):
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrWorkshopReadOnly]

    def get_queryset(self):
        user = self.request.user

        # 🛠 Workshop → faqat read
        if user.role == 'WORKSHOP':
            return ServiceType.objects.all()

        # 👑 Admin → hammasi
        if user.role == 'ADMIN':
            return ServiceType.objects.all()

        return ServiceType.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'ADMIN':
            serializer.save()
        else:
            raise PermissionDenied("Only Admin can create service types")


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

        service = serializer.save(workshop=user.workshopprofile)

        try:
            driver_profile = service.car.owner
            if not driver_profile:
                driver_car = DriverCar.objects.select_related('driver_profile__user').filter(car=service.car).first()
                driver_profile = driver_car.driver_profile if driver_car else None

            if not driver_profile:
                return

            tokens = UserDeviceToken.objects.filter(
                user=driver_profile.user,
                is_active=True
            ).values_list('token', flat=True)

            send_push_to_tokens(
                tokens=tokens,
                title='New service created',
                body=f"{service.service_type.name} service was created by {service.workshop.title}.",
                data={
                    'event': 'service_created',
                    'service_id': str(service.id),
                    'car_id': str(service.car_id),
                },
            )
        except Exception:
            logger.exception('Failed to send service creation push notification.')

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
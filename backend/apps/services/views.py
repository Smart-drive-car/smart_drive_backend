from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
import logging
from django.db import models

from .models import ServiceType, Service
from .serializers import ServiceTypeSerializer, ServiceSerializer
from apps.users.models import UserDeviceToken
from apps.shared.push_notifications import send_push_to_tokens, send_notification_to_user
from apps.vehicles.models import DriverCar


logger = logging.getLogger(__name__)
from .permissions import IsWorkshopOrReadOnly, IsAdminOnly, IsServiceTypeOwnerOrAdmin, IsAdminOrReadOnly


# 🔹 ServiceType → ADMIN (global) + WORKSHOP & DRIVER (read only)
class ServiceTypeViewSet(viewsets.ModelViewSet):
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user

        # 🛠 Workshop & 🚗 Driver → faqat read
        if user.role in ['WORKSHOP', 'DRIVER']:
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
    filter_backends = [filters.SearchFilter]
    search_fields = ['service_type__name', 'workshop__title', 'car__car_plate_number', 'description']

    def get_queryset(self):
        user = self.request.user
        car_id = self.request.query_params.get('car_id')

        if getattr(self, 'action', '') == 'list' and user.role == 'DRIVER':
            if not car_id:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"car_id": "car_id query parameter is required to fetch services."})

        # 🛠 Workshop → faqat o'z service
        if user.role == 'WORKSHOP':
            qs = Service.objects.filter(workshop=user.workshopprofile)
            if getattr(self, 'action', '') == 'list' and car_id:
                qs = qs.filter(car_id=car_id)
            return qs

        # 🚗 Driver → faqat o'z mashinalariga tegishli service
        if user.role == 'DRIVER':
            qs = Service.objects.filter(
                car__drivercar__driver_profile=user.driverprofile
            )
            if getattr(self, 'action', '') == 'list' and car_id:
                qs = qs.filter(car_id=car_id)
            return qs

        # 👑 Admin → hammasi
        if user.role == 'ADMIN':
            qs = Service.objects.all()
            if getattr(self, 'action', '') == 'list' and car_id:
                qs = qs.filter(car_id=car_id)
            return qs

        return Service.objects.none()

    def create(self, request, *args, **kwargs):
        from rest_framework import status
        from rest_framework.response import Response
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = self.request.user
        if user.role != 'WORKSHOP':
            raise PermissionDenied("Only workshop can create service")

        service = serializer.save(workshop=user.workshopprofile)
        logger.info(f"Service created: ID={service.id}, Car ID={service.car_id}")
        
        notification_result = None
        
        try:
            driver_profile = service.car.owner
            if not driver_profile:
                driver_car = DriverCar.objects.select_related('driver_profile__user').filter(car=service.car).first()
                driver_profile = driver_car.driver_profile if driver_car else None

            if not driver_profile:
                logger.warning(f"No driver profile found for car {service.car_id}. Skipping notification.")
            else:
                logger.info(f"Preparing to send notification to User ID={driver_profile.user.id}")
                
                notification_data = {
                    'event': 'service_created',
                    'service_id': str(service.id),
                    'car_id': str(service.car_id),
                }
                
                first_image = service.workshop.images.first()
                if first_image and first_image.image:
                    try:
                        notification_data['image'] = self.request.build_absolute_uri(first_image.image.url)
                    except Exception as img_e:
                        logger.warning(f"Failed to get image url: {img_e}")
                        
                # Set title to service description if available, otherwise workshop name
                title_text = service.description if service.description else service.workshop.title

                notification_result = send_notification_to_user(
                    user=driver_profile.user,
                    title=title_text,
                    body=f"{service.service_type.name} service was created by {service.workshop.title}.",
                    data=notification_data,
                )
                logger.info(f"Push notification send result for Service ID {service.id}: {notification_result}")
        except Exception as e:
            logger.error(f"Failed to send service creation push notification: {repr(e)}")

        headers = self.get_success_headers(serializer.data)
        response_data = serializer.data
        if notification_result:
            response_data["notification_result"] = notification_result
            
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        service = self.get_object()
        user = self.request.user

        if user.role == 'WORKSHOP':
            if service.workshop != user.workshopprofile:
                raise PermissionDenied("You can update only your services")

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Deleting a service is permanently disabled to maintain accurate vehicle service history.")
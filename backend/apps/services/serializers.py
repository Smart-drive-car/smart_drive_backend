from rest_framework import serializers
from .models import ServiceType, Service
from apps.vehicles.models import DriverCar


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'
        read_only_fields = ['workshop']

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        car = attrs.get('car')

        # 🚗 Driver faqat o'z mashinasini ishlata oladi
        if user.role == 'DRIVER' and car:
            if not DriverCar.objects.filter(
                driver_profile=user.driverprofile,
                car=car
            ).exists():
                raise serializers.ValidationError("You can use only your own car")

        return attrs

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')

        # Only add expanded details for GET requests
        if request and request.method == 'GET':
            # Workshop Details
            if instance.workshop:
                workshop_image_url = None
                workshop_image = instance.workshop.images.first()  # Get first available image
                if workshop_image and workshop_image.image:
                    workshop_image_url = request.build_absolute_uri(workshop_image.image.url)

                representation['workshop'] = {
                    "id": instance.workshop.id,
                    "title": instance.workshop.title,
                    "address": instance.workshop.address,
                    "phone_number": str(instance.workshop.user.phone_number) if instance.workshop.user else None,
                    "image": workshop_image_url,
                    "lat": float(instance.workshop.latitude) if instance.workshop.latitude else None,
                    "lng": float(instance.workshop.longitude) if instance.workshop.longitude else None,
                }

            # Service Type Details
            if instance.service_type:
                representation['service_type'] = {
                    "id": instance.service_type.id,
                    "name": instance.service_type.name,
                }

            # Car Details
            if instance.car:
                car = instance.car
                vehicle_data = None
                if car.vehicle_model:
                    vehicle_data = {
                        "brand": car.vehicle_model.brand.name if car.vehicle_model.brand else None,
                        "model": car.vehicle_model.model_name
                    }
                
                representation['car'] = {
                    "id": car.id,
                    "car_plate_number": car.car_plate_number,
                    "vehicle": vehicle_data
                }

                # Driver Details (tied to car)
                driver_profile = car.owner
                if not driver_profile:
                    driver_car = car.drivercar_set.first()
                    if driver_car:
                        driver_profile = driver_car.driver_profile

                if driver_profile:
                    representation['driver'] = {
                        "id": driver_profile.id,
                        "full_name": driver_profile.full_name,
                        "phone_number": str(driver_profile.user.phone_number) if driver_profile.user else None,
                        "image": request.build_absolute_uri(driver_profile.image.url) if driver_profile.image else None,
                    }
                else:
                    representation['driver'] = None

        return representation
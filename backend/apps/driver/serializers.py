from rest_framework import serializers

from apps.vehicles.models import DriverCar

from .models import DriverProfile


class DriverProfileLoginSerializer(serializers.ModelSerializer):
    cars = serializers.SerializerMethodField()

    class Meta:
        model = DriverProfile
        fields = ['full_name', 'image', 'cars']

    def get_cars(self, obj):
        from apps.services.models import Service
        car_links = DriverCar.objects.filter(driver_profile=obj).select_related('car', 'car__vehicle_model', 'car__vehicle_model__brand')
        from apps.vehicles.serializers import VehicleModelSerializer
        
        cars_data = []
        for link in car_links:
            car = link.car
            service = Service.objects.filter(car=car, service_type__name__icontains="moy").order_by('-created_at').first()
            if not service:
                service = Service.objects.filter(car=car, service_type__name__icontains="oil").order_by('-created_at').first()
                if not service:
                    service = Service.objects.filter(car=car).order_by('-created_at').first()
            
            last_service = None
            service_status = None

            if service:
                last_service = {"id": service.id, "workshop_name": service.workshop.title if service.workshop else "", "service_type": service.service_type.name if service.service_type else "", "interval": service.probeg, "performed_at_mileage": service.performed_at_mileage}
                if service.performed_at_mileage is not None and service.probeg is not None:
                    current = car.current_mileage or 0
                    dist = current - service.performed_at_mileage
                    nxt = service.performed_at_mileage + service.probeg
                    rem = nxt - current
                    service_status = {"distance_traveled": max(0, dist), "next_service_at": nxt, "remaining_distance": abs(rem), "is_overdue": rem < 0}

            cars_data.append({
                "id": car.id, "plate": car.car_plate_number, "model_id": car.vehicle_model.id if car.vehicle_model else None, "vehicle_model": VehicleModelSerializer(car.vehicle_model).data if car.vehicle_model else None, "mileage": car.current_mileage, "last_service": last_service, "service_status": service_status
            })
            
        return cars_data


class DriverProfileUpdateSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, required=False, min_length=8, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = DriverProfile
        fields = ['full_name', 'image', 'old_password', 'new_password', 'new_password_confirm']

    def validate(self, attrs):
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')

        if old_password or new_password or new_password_confirm:
            if not all([old_password, new_password, new_password_confirm]):
                raise serializers.ValidationError(
                    "To change password, provide old_password, new_password, and new_password_confirm."
                )
            if new_password != new_password_confirm:
                raise serializers.ValidationError({"new_password": "Passwords do not match."})

            user = self.instance.user
            if not user.check_password(old_password):
                raise serializers.ValidationError({"old_password": "Old password is incorrect."})

        return attrs

    def update(self, instance, validated_data):
        validated_data.pop('old_password', None)
        new_password = validated_data.pop('new_password', None)
        validated_data.pop('new_password_confirm', None)

        instance = super().update(instance, validated_data)

        if new_password:
            user = instance.user
            user.set_password(new_password)
            user.save()

        return instance

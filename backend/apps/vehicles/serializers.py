# apps/vehicles/serializers.py
from rest_framework import serializers
from .models import Car, DriverCar, VehicleModel, VehicleBrand

class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = ['id', 'name']

class VehicleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleModel
        fields = ['id', 'brand', 'model_name']

class CarCreateSerializer(serializers.ModelSerializer):
    # We accept the ID of the model from the frontend
    vehicle_model_id = serializers.PrimaryKeyRelatedField(
        queryset=VehicleModel.objects.all(), 
        source='vehicle_model',
        write_only=True
    )

    class Meta:
        model = Car
        fields = ['car_plate_number', 'current_mileage', 'vehicle_model_id']

    def validate_car_plate_number(self, value):
        # Clean the plate: Remove spaces and make uppercase
        return value.strip().upper().replace(" ", "")

    def create(self, validated_data):
        user = self.context['request'].user
        plate = validated_data.get('car_plate_number')

        # 1. Get or Create the physical Car
        # We use update_or_create in case the car exists but the mileage needs updating
        car, created = Car.objects.get_or_create(
            car_plate_number=plate,
            defaults={
                'vehicle_model': validated_data.get('vehicle_model'),
                'current_mileage': validated_data.get('current_mileage')
            }
        )

        # 2. Link the car to the Driver's profile
        # .get_or_create prevents duplicate links if they submit twice
        DriverCar.objects.get_or_create(
            driver_profile=user.driverprofile,
            car=car
        )

        return car
# apps/vehicles/serializers.py
from rest_framework import serializers
from .models import Car, DriverCar, VehicleModel, VehicleBrand

class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = ['id', 'name']

class VehicleModelSerializer(serializers.ModelSerializer):
    brand = VehicleBrandSerializer(read_only=True)
    
    class Meta:
        model = VehicleModel
        fields = ['id', 'brand', 'model_name', 'image']

class CarUpdateSerializer(serializers.ModelSerializer):
    vehicle_model_id = serializers.PrimaryKeyRelatedField(
        queryset=VehicleModel.objects.all(),
        source='vehicle_model',
        write_only=True,
        required=False
    )
    vehicle_model = VehicleModelSerializer(read_only=True)
    current_mileage = serializers.IntegerField(required=False, min_value=0)
    car_plate_number = serializers.CharField(max_length=20, required=False, allow_blank=False)

    class Meta:
        model = Car
        fields = ['id', 'car_plate_number', 'current_mileage', 'vehicle_model_id', 'vehicle_model']

    def validate_car_plate_number(self, value):
        if value:
            plate_number = value.strip().upper().replace(" ", "")
            if Car.objects.filter(car_plate_number=plate_number).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise serializers.ValidationError("A car with this plate number already exists.")
            return plate_number
        return value

class CarCreateSerializer(serializers.ModelSerializer):
    # We accept the ID of the model from the frontend
    vehicle_model_id = serializers.PrimaryKeyRelatedField(
        queryset=VehicleModel.objects.all(),
        source='vehicle_model',
        write_only=True
    )
    vehicle_model = VehicleModelSerializer(read_only=True)

    car_plate_number = serializers.CharField(max_length=20, required=True, allow_blank=False)
    current_mileage = serializers.IntegerField(required=False, default=0, min_value=0)

    class Meta:
        model = Car
        fields = ['id', 'car_plate_number', 'current_mileage', 'vehicle_model_id', 'vehicle_model']

    def validate_car_plate_number(self, value):
        # Clean the plate: Remove spaces and make uppercase
        plate_number = value.strip().upper().replace(" ", "")
        
        if Car.objects.filter(car_plate_number=plate_number).exists():
            raise serializers.ValidationError("A car with this plate number already exists.")
            
        return plate_number

    def create(self, validated_data):
        user = self.context['request'].user
        driver_profile = user.driverprofile
        plate = validated_data.get('car_plate_number')

        # Create the car with owner set to the current driver
        car = Car.objects.create(
            owner=driver_profile,
            car_plate_number=plate,
            vehicle_model=validated_data.get('vehicle_model'),
            current_mileage=validated_data.get('current_mileage')
        )

        # Link the car to the Driver's profile via DriverCar for backward compatibility
        DriverCar.objects.get_or_create(
            driver_profile=driver_profile,
            car=car
        )
        #add vehicle model to car data and return it
        car.vehicle_model = validated_data.get('vehicle_model') 
        return car 
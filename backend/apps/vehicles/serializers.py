# apps/vehicles/serializers.py
from rest_framework import serializers
from .models import Car, DriverCar, VehicleModel, VehicleBrand
from apps.services.models import Service
from apps.services.models import Service

class GPSPointSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    timestamp = serializers.DateTimeField()
    speed = serializers.FloatField(required=False)
    accuracy = serializers.FloatField(required=False)

class MileageBatchSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    trip_id = serializers.CharField(max_length=100, required=False)
    points = GPSPointSerializer(many=True)

    def validate_points(self, points):
        if not points:
            raise serializers.ValidationError("Points array cannot be empty.")
        
        # Sort points by timestamp to ensure chronological order
        points.sort(key=lambda x: x['timestamp'])
        
        # Validate logical timestamps (no future dates)
        from django.utils import timezone
        now = timezone.now()
        for point in points:
            if point['timestamp'] > now:
                raise serializers.ValidationError("Timestamp cannot be in the future.")
                
        return points

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
    current_mileage = serializers.FloatField(required=False, min_value=0.0)
    released_year = serializers.IntegerField(required=False, min_value=1886)
    car_plate_number = serializers.CharField(max_length=20, required=False, allow_blank=False)

    last_service = serializers.SerializerMethodField()
    service_status = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = ['id', 'car_plate_number', 'released_year', 'current_mileage', 'vehicle_model_id', 'vehicle_model', 'last_service', 'service_status']

    def get_last_service(self, obj):
        service = Service.objects.filter(car=obj, service_type__name__icontains="moy").order_by('-created_at').first()
        if not service:
            service = Service.objects.filter(car=obj, service_type__name__icontains="oil").order_by('-created_at').first()
            if not service:
                service = Service.objects.filter(car=obj).order_by('-created_at').first()
        
        if not service:
            return None
        return {
            "id": service.id,
            "workshop_name": service.workshop.title if service.workshop else "",
            "service_type": service.service_type.name if service.service_type else "",
            "interval": service.probeg,
            "performed_at_mileage": service.performed_at_mileage
        }

    def get_service_status(self, obj):
        service = Service.objects.filter(car=obj, service_type__name__icontains="moy").order_by('-created_at').first()
        if not service:
            service = Service.objects.filter(car=obj, service_type__name__icontains="oil").order_by('-created_at').first()
            if not service:
                service = Service.objects.filter(car=obj).order_by('-created_at').first()

        if not service or service.performed_at_mileage is None or service.probeg is None:
            return None

        current = obj.current_mileage or 0
        distance_traveled = current - service.performed_at_mileage
        next_service_at = service.performed_at_mileage + service.probeg
        remaining_distance = next_service_at - current

        return {
            "distance_traveled": max(0, distance_traveled),
            "next_service_at": next_service_at,
            "remaining_distance": abs(remaining_distance),
            "is_overdue": remaining_distance < 0
        }

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
    released_year = serializers.IntegerField(required=False, allow_null=True, min_value=1886)
    current_mileage = serializers.FloatField(required=False, default=0.0, min_value=0.0)

    class Meta:
        model = Car
        fields = ['id', 'car_plate_number', 'released_year', 'current_mileage', 'vehicle_model_id', 'vehicle_model']

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
        current_mileage = validated_data.get('current_mileage', 0.0)
        car = Car.objects.create(
            owner=driver_profile,
            car_plate_number=plate,
            vehicle_model=validated_data.get('vehicle_model'),
            released_year=validated_data.get('released_year'),
            current_mileage=current_mileage,
            initial_mileage=current_mileage
        )

        # Link the car to the Driver's profile via DriverCar for backward compatibility
        DriverCar.objects.get_or_create(
            driver_profile=driver_profile,
            car=car
        )
        #add vehicle model to car data and return it
        car.vehicle_model = validated_data.get('vehicle_model') 
        return car 
    



class CarSearchSerializer(serializers.ModelSerializer):
    driver = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = [
            'id',
            'car_plate_number',
            'vehicle',
            'driver'
        ]

    def get_driver(self, obj):
        if obj.owner:
            return {
                "full_name": obj.owner.full_name,
                "phone_number": obj.owner.user.phone_number,
                "image": obj.owner.image.url if obj.owner.image else None 
            }
        return None

    def get_vehicle(self, obj):
        if obj.vehicle_model:
            return {
                "brand": obj.vehicle_model.brand.name,
                "model": obj.vehicle_model.model_name
            }
        return None
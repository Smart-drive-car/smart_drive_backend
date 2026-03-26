from rest_framework import serializers
from .models import ServiceType, Service
from apps.vehicles.models import DriverCar


class ServiceTypeSerializer(serializers.ModelSerializer):
    is_global = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ServiceType
        fields = ["id", "name", "owner", "is_global", "created_at", "updated_at"]
        read_only_fields = ["owner", "is_global", "created_at", "updated_at"]

    def get_is_global(self, obj):
        return obj.owner is None


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
        if user.role == 'DRIVER':
            if not DriverCar.objects.filter(
                driver_profile=user.driverprofile,
                car=car
            ).exists():
                raise serializers.ValidationError("You can use only your own car")

        return attrs
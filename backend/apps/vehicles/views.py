from django.shortcuts import render
from .serializers import CarCreateSerializer, CarUpdateSerializer, VehicleBrandSerializer, VehicleModelSerializer
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Car, DriverCar, VehicleBrand, VehicleModel
from .permissions import IsOwnerOrReadOnly

# apps/vehicles/views.py
from apps.users.models import Role


class VehicleCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CarCreateSerializer

    def perform_create(self, serializer):
        # Safety check: Only Drivers have a DriverProfile
        if self.request.user.role != Role.DRIVER:
            raise PermissionDenied("Only accounts with the 'Driver' role can add vehicles.")
        #it should check if this car exist in drivercar table, if exist it should not create new car and return error
        car_plate_number = serializer.validated_data.get('car_plate_number')
        if DriverCar.objects.filter(car__car_plate_number=car_plate_number).exists():
            raise serializers.ValidationError("A car with this plate number is already associated with your profile.")
        serializer.save()

class VehicleRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Car.objects.all()
    serializer_class = CarUpdateSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        # Additional safety: ensure users can only query their own cars
        # If admin needs access, we can adjust here.
        if self.request.user.role == Role.DRIVER:
            return Car.objects.filter(owner=self.request.user.driverprofile)
        return Car.objects.none()

class VehicleBrandListView(generics.ListAPIView):
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer
    permission_classes = [IsAuthenticated]

class VehicleModelListView(generics.ListAPIView):
    serializer_class = VehicleModelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Optional: Filter models by brand if 'brand_id' is in URL params
        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            return VehicleModel.objects.filter(brand_id=brand_id)
        return VehicleModel.objects.all()
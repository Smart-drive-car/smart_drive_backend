from django.shortcuts import render
from .serializers import CarCreateSerializer, VehicleBrandSerializer, VehicleModelSerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import DriverCar, VehicleBrand, VehicleModel
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
        serializer.save()


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
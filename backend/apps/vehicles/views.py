from django.shortcuts import render
from .serializers import CarCreateSerializer, CarUpdateSerializer, VehicleBrandSerializer, VehicleModelSerializer,CarSearchSerializer
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Car, DriverCar, VehicleBrand, VehicleModel
from .permissions import IsOwnerOrReadOnly, IsWorkshopOrAdmin
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from drf_spectacular.utils import extend_schema
from .serializers import MileageBatchSerializer
from .utils import clean_gps_points, calculate_total_distance


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
        user = self.request.user
        if user.role == Role.DRIVER:
            return Car.objects.filter(owner=user.driverprofile)
        elif user.role in [Role.WORKSHOP, Role.ADMIN]:
            return Car.objects.all()
        return Car.objects.none()

    def perform_update(self, serializer):
        instance = self.get_object()
        old_mileage = instance.current_mileage or 0
        updated_car = serializer.save()
        
        try:
            if hasattr(updated_car, 'current_mileage') and updated_car.current_mileage != old_mileage:
                from apps.vehicles.utils import check_and_send_service_warnings
                check_and_send_service_warnings(updated_car, old_mileage)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error checking notifications during manual mileage update: {e}")

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
    




class CarSearchView(generics.ListAPIView):
    serializer_class = CarSearchSerializer
    permission_classes = [IsWorkshopOrAdmin]

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip().upper().replace(" ", "")


        queryset = Car.objects.select_related(
            'owner__user',
            'vehicle_model__brand'
        )

        # 🔍 Search (partial + flexible)
        queryset = queryset.filter(
            Q(car_plate_number__icontains=query)
        )

        return queryset.order_by('-created_at')[:10]  # limit 10 ta natija

class UpdateMileageView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=MileageBatchSerializer,
        responses={200: MileageBatchSerializer},
        summary="Update the mileage of a car",
        description="Receive a batch of GPS points, clean the data, calculate real distance, and update total car mileage."
    )
    def post(self, request):
        if request.user.role != Role.DRIVER:
             raise PermissionDenied("Only drivers can update mileage.")

        serializer = MileageBatchSerializer(data=request.data)
        if serializer.is_valid():
            car_id = serializer.validated_data['car_id']
            raw_points = serializer.validated_data['points']
            
            # Step 3: Clean data
            cleaned_points = clean_gps_points(raw_points)
            
            # Step 4: Calculate distance
            distance_travelled_km = calculate_total_distance(cleaned_points)
            
            # Step 5: Update the database safely
            try:
                with transaction.atomic():
                    # select_for_update() prevents race conditions if multiple batches arrive fast
                    car = Car.objects.select_for_update().get(id=car_id, owner=request.user.driverprofile)

                    old_mileage = car.current_mileage or 0
                    if not car.current_mileage:
                        car.current_mileage = 0

                    car.current_mileage += distance_travelled_km
                    car.save()

                    try:
                        from apps.vehicles.utils import check_and_send_service_warnings
                        check_and_send_service_warnings(car, old_mileage)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Error checking notifications: {e}")

                    try:
                        from apps.vehicles.utils import check_and_send_service_warnings
                        check_and_send_service_warnings(car, old_mileage)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Error checking notifications: {e}")
                    
            except Car.DoesNotExist:
                return Response({"error": "Car not found or you are not the owner."}, status=status.HTTP_404_NOT_FOUND)
                
            # Step 6: Return new total to Flutter
            return Response({
                "message": "Mileage updated",
                "distance_added_km": round(distance_travelled_km, 3),
                "new_current_mileage": car.current_mileage
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DriverCarListView(generics.ListAPIView):
    serializer_class = CarUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == Role.DRIVER:
            return Car.objects.filter(owner=user.driverprofile).select_related('vehicle_model', 'vehicle_model__brand')
        return Car.objects.none()

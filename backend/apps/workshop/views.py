from rest_framework import status
from django.db.models import Avg, Count, FloatField, Value, Q
from django.db.models.functions import Coalesce
from rest_framework.generics import UpdateAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import NotFound

from apps.users.permissions import IsDriver, IsWorkshop

from .models import WorkshopProfile
from .permissions import IsOwnWorkshopProfile
from .serializers import (
    WorkshopProfileUpdateSerializer,
    WorkshopProfileListSerializer,
    WorkshopDetailSerializer,
    WorkshopRatingSerializer,
)


class WorkshopProfileUpdateView(UpdateAPIView):
    permission_classes = [IsAuthenticated, IsWorkshop, IsOwnWorkshopProfile]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = WorkshopProfileUpdateSerializer

    def get_object(self):
        return self.request.user.workshopprofile

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.get('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response({"message": "Workshop profile updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"error": "Failed to update profile", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class WorkshopListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsDriver]
    serializer_class = WorkshopProfileListSerializer

    def get_queryset(self):
        queryset = WorkshopProfile.objects.all().prefetch_related('images').annotate(
            total_customers=Count('service__car__owner', distinct=True),
            average_rating=Coalesce(
                Avg('ratings__rating'),
                Value(0.0),
                output_field=FloatField(),
            ),
        )
        title = self.request.query_params.get('title')
        if title:
            query = title.strip()
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(address__icontains=query)
            )
        return queryset


class WorkshopDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_workshop(self, pk):
        try:
            return WorkshopProfile.objects.prefetch_related('images').annotate(
                total_customers=Count('service__car__owner', distinct=True),
                average_rating=Coalesce(
                    Avg('ratings__rating'),
                    Value(0.0),
                    output_field=FloatField(),
                ),
            ).get(pk=pk)
        except WorkshopProfile.DoesNotExist:
            raise NotFound("Workshop not found.")

    def get(self, request, pk):
        workshop = self.get_workshop(pk)
        data = WorkshopDetailSerializer(workshop).data
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        if not IsDriver().has_permission(request, self):
            raise PermissionDenied("Only drivers can rate workshop.")

        serializer = WorkshopRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workshop = self.get_workshop(pk)
        rating_obj, created = workshop.ratings.update_or_create(
            driver=request.user.driverprofile,
            defaults={'rating': serializer.validated_data['rating']}
        )

        workshop = self.get_workshop(pk)
        return Response(
            {
                'message': 'Workshop rated successfully.' if created else 'Workshop rating updated successfully.',
                'data': WorkshopDetailSerializer(workshop).data,
                'your_rating': rating_obj.rating,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

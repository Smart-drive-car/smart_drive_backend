from rest_framework import status
from rest_framework.generics import UpdateAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsDriver, IsWorkshop

from .models import WorkshopProfile
from .permissions import IsOwnWorkshopProfile
from .serializers import WorkshopProfileUpdateSerializer, WorkshopProfileListSerializer


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
        queryset = WorkshopProfile.objects.all().prefetch_related('images')
        title = self.request.query_params.get('title')
        if title:
            queryset = queryset.filter(title__icontains=title.strip())
        return queryset

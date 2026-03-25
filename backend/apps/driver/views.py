from rest_framework import status
from rest_framework.generics import UpdateAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsDriver

from .permissions import IsOwnDriverProfile
from .serializers import DriverProfileUpdateSerializer


class DriverProfileUpdateView(UpdateAPIView):
    permission_classes = [IsAuthenticated, IsDriver, IsOwnDriverProfile]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = DriverProfileUpdateSerializer

    def get_object(self):
        return self.request.user.driverprofile

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.get('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response({"message": "Driver profile updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"error": "Failed to update profile", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

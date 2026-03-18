from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import ServiceType, Service
from .serializers import ServiceTypeSerializer, ServiceSerializer
from .permissions import IsAdmin, IsWorkshop


class ServiceTypeViewSet(viewsets.ModelViewSet):
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated, IsWorkshop]

    def get_queryset(self):
        user = self.request.user

        # faqat o‘z workshop service’larini ko‘radi
        return Service.objects.filter(workshop=user.workshopprofile)
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer

from drf_spectacular.utils import extend_schema

class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user).order_by('-created_at')
        
        if getattr(self, 'action', '') in ['list', 'mark_all_read']:
            car_id = self.request.query_params.get('car_id')
            # Require car_id optionally, or strictly? If strictly:
            if not car_id:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"car_id": "car_id query parameter is required."})
            qs = qs.filter(data__car_id=str(car_id))
            
        return qs

    @extend_schema(request=None)
    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated_count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'message': f'{updated_count} notifications marked as read.'})

    @extend_schema(request=None)
    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read.', 'is_read': True})


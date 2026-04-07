from rest_framework import serializers
from .models import Notification
from .notification_i18n import localize_notification

class NotificationSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()

    def _localized_payload(self, obj):
        return localize_notification(
            title=obj.title,
            body=obj.body,
            data=obj.data,
        )

    def get_title(self, obj):
        return self._localized_payload(obj)["title"]

    def get_body(self, obj):
        return self._localized_payload(obj)["body"]

    class Meta:
        model = Notification
        fields = ['id', 'title', 'body', 'is_read', 'data', 'created_at']
        read_only_fields = ['id', 'title', 'body', 'data', 'created_at']


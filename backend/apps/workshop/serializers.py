import re

from django.db import transaction
from django.db.utils import ProgrammingError, OperationalError
from rest_framework import serializers

from .models import WorkshopProfile, WorkshopProfileImages, WorkshopRating


WORKING_TIME_PATTERN = re.compile(r'^\s*([01]\d|2[0-3]):([0-5]\d)\s*-\s*([01]\d|2[0-3]):([0-5]\d)\s*$')


def validate_working_time_format(value):
    if value in (None, ''):
        return value

    match = WORKING_TIME_PATTERN.match(value)
    if not match:
        raise serializers.ValidationError("working_time must be in HH:MM-HH:MM format.")

    start_hour, start_minute, end_hour, end_minute = map(int, match.groups())
    start_total = (start_hour * 60) + start_minute
    end_total = (end_hour * 60) + end_minute

    if start_total == end_total:
        raise serializers.ValidationError("working_time start and end time cannot be the same.")

    return f"{start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d}"


class WorkshopProfileLoginSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()

    class Meta:
        model = WorkshopProfile
        fields = ['title', 'address', 'description', 'working_time', 'latitude', 'longitude', 'images']

    def get_images(self, obj):
        try:
            return [{'id': img.id, 'image': img.image.url} for img in obj.images.all()]
        except Exception:
            return []


class WorkshopProfileListSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    total_customers = serializers.IntegerField(read_only=True)
    rating = serializers.FloatField(source='average_rating', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = WorkshopProfile
        fields = ['id', 'title', 'address', 'description', 'working_time', 'latitude', 'longitude', 'images', 'total_customers', 'rating', 'phone_number']

    def get_images(self, obj):
        try:
            return [{'id': img.id, 'image': img.image.url} for img in obj.images.all()]
        except Exception:
            return []


class WorkshopDetailSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    total_customers = serializers.IntegerField(read_only=True)
    rating = serializers.FloatField(source='average_rating', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = WorkshopProfile
        fields = [
            'id', 'title', 'address', 'description', 'working_time',
            'latitude', 'longitude', 'images', 'total_customers', 'rating', 'phone_number'
        ]

    def get_images(self, obj):
        try:
            return [{'id': img.id, 'image': img.image.url} for img in obj.images.all()]
        except Exception:
            return []


class WorkshopProfileUpdateSerializer(serializers.ModelSerializer):
    working_time = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    workshop_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=True, required=False, allow_null=True),
        required=False,
        allow_empty=True,
        allow_null=True,
        write_only=True
    )
    deleted_image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="Provide a list of image IDs you wish to delete."
    )
    old_password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, required=False, min_length=8, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    images = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WorkshopProfile
        fields = ['title', 'address', 'description', 'working_time', 'latitude', 'longitude', 'images', 'workshop_images', 'deleted_image_ids', 'old_password', 'new_password', 'new_password_confirm']

    def get_images(self, obj):
        try:
            return [{'id': img.id, 'image': img.image.url} for img in obj.images.all()]
        except Exception:
            return []

    def validate(self, attrs):
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')

        if old_password or new_password or new_password_confirm:
            if not all([old_password, new_password, new_password_confirm]):
                raise serializers.ValidationError(
                    "To change password, provide old_password, new_password, and new_password_confirm."
                )
            if new_password != new_password_confirm:
                raise serializers.ValidationError({"new_password": "Passwords do not match."})

            user = self.instance.user
            if not user.check_password(old_password):
                raise serializers.ValidationError({"old_password": "Old password is incorrect."})

        return attrs

    def validate_working_time(self, value):
        return validate_working_time_format(value)

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else data
        if 'workshop_images' in data:
            from django.core.files.uploadedfile import UploadedFile
            images = data.getlist('workshop_images') if hasattr(data, 'getlist') else data.get('workshop_images', [])
            valid_images = [img for img in images if isinstance(img, UploadedFile)]
            if hasattr(data, 'setlist'):
                data.setlist('workshop_images', valid_images)
            else:
                data['workshop_images'] = valid_images
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        validated_data.pop('old_password', None)
        new_password = validated_data.pop('new_password', None)
        validated_data.pop('new_password_confirm', None)
        workshop_images = validated_data.pop('workshop_images', None)
        deleted_image_ids = validated_data.pop('deleted_image_ids', [])

        with transaction.atomic():
            try:
                instance = super().update(instance, validated_data)
            except (ProgrammingError, OperationalError):
                raise serializers.ValidationError({
                    "error": "Database schema is out of date. Please run migrations."
                })

            if new_password:
                user = instance.user
                user.set_password(new_password)
                user.save()

            if deleted_image_ids:
                instance.images.filter(id__in=deleted_image_ids).delete()

            if workshop_images:
                for img in workshop_images:
                    if img:
                        WorkshopProfileImages.objects.create(
                            workshop_profile=instance,
                            image=img
                        )
            return instance


class WorkshopRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopRating
        fields = ['rating']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

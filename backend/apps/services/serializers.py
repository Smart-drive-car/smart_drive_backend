from rest_framework import serializers
from .models import ServiceType, Service


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = '__all__'

    def validate(self, attrs):
        user = self.context['request'].user

        if user.role != 'ADMIN':
            raise serializers.ValidationError("Only ADMIN can create ServiceType")

        return attrs


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'
        read_only_fields = ['workshop'] 

    def validate(self, attrs):
        user = self.context['request'].user

        if user.role != 'WORKSHOP':
            raise serializers.ValidationError("Only WORKSHOP can create Service")

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user

        # workshopni avtomatik qo‘shamiz
        validated_data['workshop'] = user.workshopprofile

        return super().create(validated_data)
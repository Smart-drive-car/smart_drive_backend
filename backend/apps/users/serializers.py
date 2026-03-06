from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import DriverProfile, WorkshopProfile, DriverProfileImages, WorkshopProfileImages, Role


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            
        }
        return data
    


class DriverProfileImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfileImages
        fields = ['id', 'image']

class WorkshopProfileImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopProfileImages
        fields = ['id', 'image']



class DriverProfileSerializer(serializers.ModelSerializer):
    image = DriverProfileImagesSerializer(read_only=True)

    class Meta:
        model = DriverProfile
        fields = ['id', 'full_name', 'images']

class WorkshopProfileSerializer(serializers.ModelSerializer):
    images = WorkshopProfileImagesSerializer(read_only=True)

    class Meta:
        model = WorkshopProfile
        fields = ['id', 'title', 'address', 'images']
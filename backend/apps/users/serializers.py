from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import DriverProfile, WorkshopProfile, AdminProfile, WorkshopProfileImages
from apps.vehicles.models import DriverCar, Car
from .models import User, Role
from django.db import transaction
import re
import firebase_admin
from firebase_admin import auth as firebase_auth
from drf_spectacular.utils import extend_schema_field
from firebase_admin import auth


# --- Small Serializers for Profile Data ---

class DriverProfileLoginSerializer(serializers.ModelSerializer):
    cars = serializers.SerializerMethodField()

    class Meta:
        model = DriverProfile
        fields = ['full_name', 'image', 'cars']

    def get_cars(self, obj):
        # Fetches cars through the DriverCar relationship
        # Only returning basic info to keep the login response fast
        car_links = DriverCar.objects.filter(driver_profile=obj).select_related('car', 'car__vehicle_model', 'car__vehicle_model__brand')
        from apps.vehicles.serializers import VehicleModelSerializer
        return [{
            "id": link.car.id,
            "plate": link.car.car_plate_number,
            "model_id": link.car.vehicle_model.id if link.car.vehicle_model else None,
            "vehicle_model": VehicleModelSerializer(link.car.vehicle_model).data if link.car.vehicle_model else None,
            "mileage": link.car.current_mileage
        } for link in car_links]

class WorkshopProfileLoginSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()

    class Meta:
        model = WorkshopProfile
        fields = ['title', 'address', 'latitude', 'longitude', 'images']

    def get_images(self, obj):
        # returns a list of image URLs
        return [img.image.url for img in obj.images.all()]

class AdminProfileLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = ['full_name']

class UserDetailSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['phone_number', 'role', 'profile']

    def get_profile(self, obj):
        if obj.role == Role.DRIVER:
            return DriverProfileLoginSerializer(getattr(obj, 'driverprofile', None)).data
        elif obj.role == Role.WORKSHOP:
            return WorkshopProfileLoginSerializer(getattr(obj, 'workshopprofile', None)).data
        elif obj.role == Role.ADMIN:
            return AdminProfileLoginSerializer(getattr(obj, 'admin_profile', None)).data
        return None


# --- Main JWT Serializer ---
class RegistrationSerializer(serializers.ModelSerializer):

    @extend_schema_field(serializers.ListField(child=serializers.FileField()))
    def get_workshop_images(self, obj): 
        # This is just for the schema generator
        pass


    # Password fields
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    # Profile fields
    full_name = serializers.CharField(required=False, write_only=True)
    image = serializers.ImageField(required=False, write_only=True,allow_null=True) # Driver Profile Pic
    
    title = serializers.CharField(required=False, write_only=True)
    address = serializers.CharField(required=False, write_only=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, write_only=True, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, write_only=True, allow_null=True)
    # List of images for Workshop
    workshop_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=True, required=False, allow_null=True),
        required=False,
        allow_empty=True,
        allow_null=True,
        write_only=True
    )

    class Meta:
        model = User
        fields = [
            'phone_number', 'password', 'password_confirm', 'role',
            'full_name', 'image', 'title', 'address', 'latitude', 'longitude', 'workshop_images'
        ]

    def to_internal_value(self, data):
        # Make a mutable copy of the data
        data = data.copy() if hasattr(data, 'copy') else data
        
        # Clean up workshop_images (Postman often sends empty strings for file fields)
        if 'workshop_images' in data:
            from django.core.files.uploadedfile import UploadedFile
            images = data.getlist('workshop_images') if hasattr(data, 'getlist') else data.get('workshop_images', [])
            valid_images = [img for img in images if isinstance(img, UploadedFile)]
            if hasattr(data, 'setlist'):
                data.setlist('workshop_images', valid_images)
            else:
                data['workshop_images'] = valid_images
                
        return super().to_internal_value(data)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        role = attrs.get('role')
        if role == Role.DRIVER:
            if not attrs.get('full_name'):
                raise serializers.ValidationError({"full_name": "Required for Drivers."})
                
        if role == Role.WORKSHOP:
            if not attrs.get('title') or not attrs.get('address'):
                raise serializers.ValidationError("Workshop needs title and address.")
            
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            # Pop all profile-specific data
            password_confirm = validated_data.pop('password_confirm')
            role = validated_data.pop('role')
            password = validated_data.pop('password')
            phone = validated_data.pop('phone_number')

            # Driver data
            full_name = validated_data.pop('full_name', None)
            driver_image = validated_data.pop('image', None)

            # Workshop data
            title = validated_data.pop('title', None)
            address = validated_data.pop('address', None)
            latitude = validated_data.pop('latitude', None)
            longitude = validated_data.pop('longitude', None)
            workshop_images = validated_data.pop('workshop_images', [])

            # 1. Create User
            user = User.objects.create_user(
                phone_number=phone,
                password=password,
                role=role,
                is_active=True,
            )

            # 2. Create specific Profile and handle images
            if role == Role.DRIVER:
                DriverProfile.objects.create(
                    user=user,
                    full_name=full_name,
                    image=driver_image
                )

            elif role == Role.WORKSHOP:
                workshop = WorkshopProfile.objects.create(
                    user=user,
                    title=title,
                    address=address,
                    latitude=latitude,
                    longitude=longitude
                )
                # Create multiple image records
                for img in workshop_images:
                    if img:  # Only save valid image files
                        WorkshopProfileImages.objects.create(
                            workshop_profile=workshop,
                            image=img
                        )

            return user



class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate_phone_number(self, value):
        clean_phone = re.sub(r'\D', '', value) # Remove all non-digits
        if len(clean_phone) >= 9: # Ensure it has at least 9 digits
            return clean_phone[-9:] # Return the last 9 digits    
        raise serializers.ValidationError("Phone number must contain at least 9 digits.")

    def validate(self, attrs):
        # 1. Get standard JWT data (access & refresh tokens)
        data = super().validate(attrs)
        
        
        # 2. Add user base info
        user = self.user
        data['user'] = {
            'phone_number': user.phone_number,
            'role': user.role,
        }

        # 3. Add dynamic profile info based on role
        if user.role == 'DRIVER':
            profile = getattr(user, 'driverprofile', None)
            data['user']['profile'] = DriverProfileLoginSerializer(profile).data if profile else None
        
        elif user.role == 'WORKSHOP':
            profile = getattr(user, 'workshopprofile', None)
            data['user']['profile'] = WorkshopProfileLoginSerializer(profile).data if profile else None
            
        elif user.role == 'ADMIN':
            profile = getattr(user, 'admin_profile', None)
            data['user']['profile'] = AdminProfileLoginSerializer(profile).data if profile else None

        return data




class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_token = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})


class SendOtpSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        """
        Cleans '+998901234567' or '998901234567' into your model's 9-digit format.
        """
        # Extract the last 9 digits to match your regex: r'^\d{9}$'
        clean_phone = re.sub(r'\D', '', value) # Remove all non-digits
        if len(clean_phone) >= 9:
            return clean_phone[-9:]
        raise serializers.ValidationError("Phone number must contain at least 9 digits.")

class RegisterConfirmSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)   

    def validate_phone_number(self, value):
        """
        Cleans '+998901234567' or '998901234567' into your model's 9-digit format.
        """
        # Extract the last 9 digits to match your regex: r'^\d{9}$'
        clean_phone = re.sub(r'\D', '', value) # Remove all non-digits
        if len(clean_phone) >= 9:
            return clean_phone[-9:]
        raise serializers.ValidationError("Phone number must contain at least 9 digits.")


class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        clean_phone = re.sub(r'\D', '', value)
        if len(clean_phone) >= 9:
            return clean_phone[-9:]
        raise serializers.ValidationError("Phone number must contain at least 9 digits.")

class TestRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)



class DriverProfileUpdateSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, required=False, min_length=8, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = DriverProfile
        fields = ['full_name', 'image', 'old_password', 'new_password', 'new_password_confirm']

    def validate(self, attrs):
        # Check if password fields are being updated
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')

        # If any password field is provided, all must be provided and match
        if old_password or new_password or new_password_confirm:
            if not all([old_password, new_password, new_password_confirm]):
                raise serializers.ValidationError(
                    "To change password, provide old_password, new_password, and new_password_confirm."
                )
            if new_password != new_password_confirm:
                raise serializers.ValidationError({"new_password": "Passwords do not match."})

        return attrs

    def update(self, instance, validated_data):
        old_password = validated_data.pop('old_password', None)
        new_password = validated_data.pop('new_password', None)
        validated_data.pop('new_password_confirm', None)

        # Update profile fields
        instance = super().update(instance, validated_data)

        # Handle password change if requested
        if old_password and new_password:
            user = instance.user
            if not user.check_password(old_password):
                raise serializers.ValidationError({"old_password": "Old password is incorrect."})
            user.set_password(new_password)
            user.save()

        return instance

class WorkshopProfileUpdateSerializer(serializers.ModelSerializer):
    workshop_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=True, required=False, allow_null=True),
        required=False,
        allow_empty=True,
        allow_null=True,
        write_only=True
    )
    old_password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, required=False, min_length=8, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = WorkshopProfile
        fields = ['title', 'address', 'latitude', 'longitude', 'workshop_images', 'old_password', 'new_password', 'new_password_confirm']

    def validate(self, attrs):
        # Check if password fields are being updated
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')

        # If any password field is provided, all must be provided and match
        if old_password or new_password or new_password_confirm:
            if not all([old_password, new_password, new_password_confirm]):
                raise serializers.ValidationError(
                    "To change password, provide old_password, new_password, and new_password_confirm."
                )
            if new_password != new_password_confirm:
                raise serializers.ValidationError({"new_password": "Passwords do not match."})

        return attrs

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
        old_password = validated_data.pop('old_password', None)
        new_password = validated_data.pop('new_password', None)
        validated_data.pop('new_password_confirm', None)
        workshop_images = validated_data.pop('workshop_images', None)

        with transaction.atomic():
            # Update profile fields
            instance = super().update(instance, validated_data)

            # Handle password change if requested
            if old_password and new_password:
                user = instance.user
                if not user.check_password(old_password):
                    raise serializers.ValidationError({"old_password": "Old password is incorrect."})
                user.set_password(new_password)
                user.save()

            # Handle image updates
            if workshop_images is not None:
                # Clear all old images when updating
                instance.images.all().delete()
                for img in workshop_images:
                    if img:
                        WorkshopProfileImages.objects.create(
                            workshop_profile=instance,
                            image=img
                        )
            return instance



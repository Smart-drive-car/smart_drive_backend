from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import AdminProfile
from apps.driver.models import DriverProfile
from apps.workshop.models import WorkshopProfile, WorkshopProfileImages
from apps.driver.serializers import DriverProfileLoginSerializer
from apps.workshop.serializers import WorkshopProfileLoginSerializer, validate_working_time_format
from .models import User, Role, DevicePlatform
from django.db import transaction
from django.db.utils import ProgrammingError, OperationalError
from drf_spectacular.utils import extend_schema_field
from .phone_utils import normalize_phone_number


# --- Small Serializers for Profile Data ---

class AdminProfileLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = ['full_name']

class UserDetailSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['phone_number', 'role', 'profile']

    def _safe_workshop_profile(self, obj):
        try:
            profile = getattr(obj, 'workshopprofile', None)
            return WorkshopProfileLoginSerializer(profile).data if profile else None
        except (ProgrammingError, OperationalError):
            return None

    def get_profile(self, obj):
        if obj.role == Role.DRIVER:
            return DriverProfileLoginSerializer(getattr(obj, 'driverprofile', None)).data
        elif obj.role == Role.WORKSHOP:
            return self._safe_workshop_profile(obj)
        elif obj.role == Role.ADMIN:
            return AdminProfileLoginSerializer(getattr(obj, 'admin_profile', None)).data
        return None


# --- Main JWT Serializer ---
class RegistrationSerializer(serializers.ModelSerializer):

    @extend_schema_field(serializers.ListField(child=serializers.FileField()))
    def get_workshop_images(self, obj): 
        # This is just for the schema generator
        pass


    phone_number = serializers.CharField(max_length=20)

    # Password fields
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    # Profile fields
    full_name = serializers.CharField(required=False, write_only=True)
    image = serializers.ImageField(required=False, write_only=True,allow_null=True) # Driver Profile Pic
    
    title = serializers.CharField(required=False, write_only=True)
    address = serializers.CharField(required=False, write_only=True)
    description = serializers.CharField(required=False, write_only=True, allow_blank=True, allow_null=True)
    working_time = serializers.CharField(required=False, write_only=True, allow_blank=True, allow_null=True)
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
            'full_name', 'image', 'title', 'address', 'description', 'working_time', 'latitude', 'longitude', 'workshop_images'
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

    def validate_working_time(self, value):
        return validate_working_time_format(value)

    def validate_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

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
            description = validated_data.pop('description', None)
            working_time = validated_data.pop('working_time', None)
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
                try:
                    workshop = WorkshopProfile.objects.create(
                        user=user,
                        title=title,
                        address=address,
                        description=description,
                        working_time=working_time,
                        latitude=latitude,
                        longitude=longitude
                    )
                except (ProgrammingError, OperationalError):
                    raise serializers.ValidationError({
                        "error": "Database schema is out of date. Please run migrations."
                    })
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
        try:
            return normalize_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def _safe_workshop_profile(self, user):
        try:
            profile = getattr(user, 'workshopprofile', None)
            return WorkshopProfileLoginSerializer(profile).data if profile else None
        except (ProgrammingError, OperationalError):
            return None

    def validate(self, attrs):
        username_field = self.username_field
        try:
            attrs[username_field] = normalize_phone_number(attrs.get(username_field, ''))
        except ValueError as exc:
            raise serializers.ValidationError({username_field: str(exc)})

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
            data['user']['profile'] = self._safe_workshop_profile(user)
            
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
        try:
            return normalize_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class ChangePhoneSendOtpSerializer(serializers.Serializer):
    new_phone_number = serializers.CharField(max_length=20)

    def validate_new_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class ChangePhoneVerifyOtpSerializer(serializers.Serializer):
    new_phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)

    def validate_new_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class DeviceTokenRegisterSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=DevicePlatform.choices)


class DeviceTokenUnregisterSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)

class RegisterConfirmSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)   

    def validate_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

class TestRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)





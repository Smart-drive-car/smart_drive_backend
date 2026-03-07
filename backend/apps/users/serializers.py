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
        car_links = DriverCar.objects.filter(driver_profile=obj).select_related('car', 'car__vehicle_model')
        return [{
            "plate": link.car.car_plate_number,
            "model": str(link.car.vehicle_model),
            "mileage": link.car.current_mileage
        } for link in car_links]

class WorkshopProfileLoginSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()

    class Meta:
        model = WorkshopProfile
        fields = ['title', 'address', 'images']

    def get_images(self, obj):
        # returns a list of image URLs
        return [img.image.url for img in obj.images.all()]

class AdminProfileLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = ['full_name']



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
    # List of images for Workshop
    workshop_images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_null=True,
        write_only=True
    )

    class Meta:
        model = User
        fields = [
            'phone_number', 'password', 'password_confirm', 'role', 
            'full_name', 'image', 'title', 'address', 'workshop_images'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        role = attrs.get('role')
        if role == Role.DRIVER:
            if not attrs.get('full_name'):
                raise serializers.ValidationError({"full_name": "Required for Drivers."})
            if not attrs.get('image'):
                raise serializers.ValidationError({"image": "Profile image is required for Drivers."})
                
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
            workshop_images = validated_data.pop('workshop_images', [])

            # 1. Create User
            user = User.objects.create_user(
                phone_number=phone,
                password=password,
                role=role,
                is_active=False,
                is_verified=False
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
                    address=address
                )
                # Create multiple image records
                for img in workshop_images:
                    WorkshopProfileImages.objects.create(
                        workshop_profile=workshop, 
                        image=img
                    )

            return user


class FirebaseVerifySerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)

    def validate_phone_number(self, value):
        """
        Cleans '+998901234567' or '998901234567' into your model's 9-digit format.
        """
        # Extract the last 9 digits to match your regex: r'^\d{9}$'
        clean_phone = re.sub(r'\D', '', value) # Remove all non-digits
        if len(clean_phone) >= 9:
            return clean_phone[-9:]
        raise serializers.ValidationError("Phone number must contain at least 9 digits.")

    def validate(self, data):
        """
        Verifies the ID Token with Firebase and checks it matches the user.
        """
        try:
            decoded_token = firebase_auth.verify_id_token(data['id_token'])
            firebase_phone = decoded_token.get('phone_number', '')
            
            # Basic security: Does the token phone match the provided phone?
            if data['phone_number'] not in firebase_phone:
                raise serializers.ValidationError("Phone number mismatch with Firebase token.")
            
            data['firebase_uid'] = decoded_token.get('uid')
            return data
        except Exception:
            raise serializers.ValidationError("Invalid or expired Firebase token.")


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
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




class PasswordResetSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    id_token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        # 1. Check passwords match
        if attrs['new_password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        # 2. Verify Firebase Token
        try:
            decoded_token = auth.verify_id_token(attrs['id_token'])
            firebase_phone = decoded_token.get('phone_number')
            
            # Basic security check: Does the token phone match the requested phone?
            # Note: Firebase phone is usually +998XXXXXXXXX
            if not firebase_phone or attrs['phone_number'] not in firebase_phone:
                raise serializers.ValidationError("Phone number does not match Firebase token.")
                
        except Exception:
            raise serializers.ValidationError("Invalid or expired Firebase token.")

        return attrs


class RegisterSerializer(serializers.Serializer):
    # Common Fields
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[Role.DRIVER, Role.WORKSHOP], default=Role.DRIVER)

    # Driver Specific Fields
    full_name = serializers.CharField(required=False, allow_blank=True)
    car_plate_number = serializers.CharField(required=False, allow_blank=True)
    vehicle_model_id = serializers.IntegerField(required=False)

    # Workshop Specific Fields
    title = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        # 1. Check Passwords
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        # 2. Check if User already exists
        if User.objects.filter(phone_number=data['phone_number']).exists():
            raise serializers.ValidationError({"phone_number": "This phone number is already registered."})

        # 3. Role-based mandatory field validation
        if data['role'] == Role.DRIVER:
            if not data.get('full_name') or not data.get('car_plate_number'):
                raise serializers.ValidationError("Drivers must provide name and plate number.")
        
        if data['role'] == Role.WORKSHOP:
            if not data.get('title') or not data.get('address'):
                raise serializers.ValidationError("Workshops must provide title and address.")

        return data


class RegisterConfirmSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)   
    

class TestRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)






from .serializers import DriverProfileUpdateSerializer, WorkshopProfileUpdateSerializer
from rest_framework.generics import UpdateAPIView
from .permissions import IsDriver, IsWorkshop, IsOwnDriverProfile, IsOwnWorkshopProfile
import re
import uuid

from django.utils import timezone
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.cache import cache
from .models import OtpVerification, User, Role, DriverProfile, UserPasswordReset, WorkshopProfile
from .serializers import TestRegisterSerializer, RegistrationSerializer, PasswordResetConfirmSerializer, CustomTokenObtainPairSerializer, ForgotPasswordSerializer, SendOtpSerializer, RegisterConfirmSerializer,UserDetailSerializer
from .utils import send_eskiz_sms, send_sms
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from firebase_admin import auth as firebase_auth
from django.shortcuts import get_object_or_404

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]




class RegisterView(GenericAPIView):
    parser_classes = (MultiPartParser, FormParser) # Necessary for images
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer


    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']

            # Ensure phone number was verified before registration
            verified_otp = OtpVerification.objects.filter(phone_number=phone, is_used=True).first()
            if not verified_otp:
                return Response(
                    {"error": "Phone number must be verified before registering."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = serializer.save()

            # Invalidate the used OTP record
            verified_otp.delete()

            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "User registered successfully.",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "user": UserDetailSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SendOtpView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = SendOtpSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']

            user = User.objects.filter(phone_number=phone).first()
            if user:
                is_login = True
            else:
                is_login = False

            otp = send_sms(phone)

            if otp:
                OtpVerification.objects.update_or_create(
                    phone_number=phone,
                    defaults={
                        "code": otp,
                        "expires_at": timezone.now() + timezone.timedelta(minutes=5),
                        "attempts": 0,
                        "is_used": False
                    }
                )

            return Response({"message": "OTP sent successfully.", "otp_code": otp, "is_login": is_login}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOtpView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            code = serializer.validated_data['code']

            otp_record = OtpVerification.objects.filter(phone_number=phone, code=code, is_used=False).first()

            if otp_record and otp_record.is_valid():
                otp_record.is_used = True
                otp_record.save()
                return Response({"message": "Phone number verified successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid or expired OTP code."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class ForgotPasswordView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']

            if not User.objects.filter(phone_number=phone).exists():
                return Response({"error": "User with this phone number not found."}, status=status.HTTP_404_NOT_FOUND)

            otp = send_sms(phone)
            if otp:
                OtpVerification.objects.update_or_create(
                    phone_number=phone,
                    defaults={
                        "code": otp,
                        "expires_at": timezone.now() + timezone.timedelta(minutes=5),
                        "attempts": 0,
                        "is_used": False
                    }
                )

            return Response({
                "message": "OTP sent to your phone number.",
                "otp_code": otp
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyPasswordResetOtpView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            code = serializer.validated_data['code']

            otp_record = OtpVerification.objects.filter(phone_number=phone, code=code, is_used=False).first()

            if not otp_record or not otp_record.is_valid():
                return Response({"error": "Invalid or expired OTP code."}, status=status.HTTP_400_BAD_REQUEST)

            otp_record.is_used = True
            otp_record.save()

            try:
                user = User.objects.get(phone_number=phone)
            except User.DoesNotExist:
                return Response({"error": "User with this phone number not found."}, status=status.HTTP_404_NOT_FOUND)

            # Create (or replace) a fresh reset token
            password_reset, _ = UserPasswordReset.objects.update_or_create(
                user=user,
                defaults={"reset_token": uuid.uuid4()}
            )

            return Response({
                "message": "OTP verified. You can now reset your password.",
                "reset_token": str(password_reset.reset_token)
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            reset_token = serializer.validated_data['reset_token']
            new_password = serializer.validated_data['new_password']

            password_reset = UserPasswordReset.objects.filter(reset_token=reset_token).first()

            if not password_reset or not password_reset.is_valid:
                return Response({"error": "Invalid or expired reset token."}, status=status.HTTP_400_BAD_REQUEST)

            user = password_reset.user
            user.set_password(new_password)
            user.save()

            password_reset.delete()

            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Password reset successfully.",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "user": UserDetailSerializer(user).data,
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(GenericAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)



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

class WorkshopProfileUpdateView(UpdateAPIView):
    permission_classes = [IsAuthenticated, IsWorkshop, IsOwnWorkshopProfile]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = WorkshopProfileUpdateSerializer

    def get_object(self):
        return self.request.user.workshopprofile

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.get('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response({"message": "Workshop profile updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"error": "Failed to update profile", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



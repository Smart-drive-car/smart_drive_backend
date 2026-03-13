

import uuid

from django.utils import timezone
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .serializers import CustomTokenObtainPairSerializer, ForgotPasswordSerializer, SendOtpSerializer, RegisterConfirmSerializer,UserDetailSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from .models import OtpCode, User, Role, DriverProfile, UserPasswordReset, WorkshopProfile
from .serializers import TestRegisterSerializer, RegistrationSerializer, PasswordResetConfirmSerializer
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
            user = serializer.save()
            otp = send_sms(serializer.validated_data['phone_number'])
            if otp:

                otp_code = OtpCode.objects.update_or_create(
                    user=user,
                    defaults={
                        "code": otp,
                        "attempts": 0,
                        "is_used": False
                    }
                )

            return Response({
                "message": "User created successfully. Please verify your phone number to activate account.",
                "phone_number": serializer.validated_data['phone_number'],
                "sms_result": otp
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
            if not user:
                return Response({"error": "User with this phone number not found."}, status=status.HTTP_404_NOT_FOUND)
            
            otp = send_sms(phone)
            
            if otp:

                otp_code = OtpCode.objects.update_or_create(
                    user=user,
                    defaults={
                        "code": otp,
                        "expires_at": timezone.now() + timezone.timedelta(minutes=5),
                        "attempts": 0,
                        "is_used": False
                    }
                )
            
            return Response({"message": "OTP sent successfully.", "otp_code": otp}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOtpView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            code = serializer.validated_data['code']
            
            try:
                user = User.objects.get(phone_number=phone)
                otp_code = OtpCode.objects.filter(user=user, code=code, is_used=False).first()
                
                
                if otp_code and otp_code.is_valid():
                    user.is_verified = True
                    user.is_active = True
                    user.save()
                    
                    otp_code.is_used = True
                    otp_code.save()
                    
                    refresh = RefreshToken.for_user(user)

                    user_data = UserDetailSerializer(user).data


                    return Response({
                        "tokens": {
                            "refresh": str(refresh),
                            "access": str(refresh.access_token),
                        },
                        "user": user_data
                        }, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid or expired OTP code."}, status=400)
            
            except User.DoesNotExist:
                return Response({"error": "User with this phone number not found."}, status=404)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class ForgotPasswordView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            
            try:
                user = User.objects.get(phone_number=phone)
                otp = send_sms(phone)
                
                if otp:

                    password_reset = UserPasswordReset.objects.update_or_create(
                        user=user,
                        defaults={
                            "code":otp,
                            "reset_token": str(uuid.uuid4()),
                            "reset_token_created_at": timezone.now(),
                            "incorrect_count": 0,
                            "otp_count": 0,
                            "verified": False
                        }
                    )
                
                return Response({
                    "message": "Password reset instructions have been sent to your phone number.",
                    "otp_code": otp
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                return Response({"error": "User with this phone number not found."}, status=404)

        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)


class VerifyPasswordResetOtpView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            code = serializer.validated_data['code']

            try:
                user = User.objects.get(phone_number=phone)
                password_reset = UserPasswordReset.objects.filter(user=user, code=code, verified=False).first()

                if password_reset and  password_reset.is_token_valid and password_reset.otp_count < 3:
                    password_reset.verified = True
                    password_reset.save()
                    
                    return Response({
                        "message": "OTP verified successfully. You can now reset your password.",
                        "reset_token": password_reset.reset_token
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid or expired OTP code."}, status=400)

            except User.DoesNotExist:
                return Response({"error": "User with this phone number not found."}, status=404)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PasswordResetConfirmView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            reset_token = serializer.validated_data['reset_token']
            new_password = serializer.validated_data['new_password']

            try:
                password_reset = UserPasswordReset.objects.filter(reset_token=reset_token, verified=True).first()
                print("Password Reset Object:", password_reset)  # Debugging line

                if password_reset and password_reset.is_token_valid:
                    user = password_reset.user
                    user.set_password(new_password)
                    user.is_active = True 
                    user.is_verified = True
                    user.save()

                    password_reset.delete()  # Invalidate the reset token after successful password reset
                    
                    return Response({
                        "message": "Password has been reset successfully. You can now log in."
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid or expired reset token."}, status=400)

            except User.DoesNotExist:
                return Response({"error": "User not found."}, status=404)

        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)


class UserDetailView(GenericAPIView):
    serializer_class = UserDetailSerializer

    def get(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

# class TestRegisterView(APIView):
#     """
#     Step 2: Check OTP and finally create User + Profile.
#     """

#     serializer_class = TestRegisterSerializer
#     permission_classes = [AllowAny]
#     def post(self, request):
#         phone = request.data.get('phone_number')
#         code = request.data.get('code')
        
#         sms_response = send_eskiz_sms(phone, f"This is test from Eskiz")
#         print("Eskiz SMS Response:", sms_response)  # Debugging line
        
#         # 2. YOU MUST RETURN A RESPONSE HERE
#         return Response({
#             "status": "processed",
#             "phone": phone,
#             "eskiz_details": sms_response
#         })
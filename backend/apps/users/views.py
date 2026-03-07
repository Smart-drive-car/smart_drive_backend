from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .serializers import CustomTokenObtainPairSerializer, RegisterConfirmSerializer, FirebaseVerifySerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from .models import OtpCode, User, Role, DriverProfile, WorkshopProfile
from .serializers import RegisterSerializer, TestRegisterSerializer, RegistrationSerializer, PasswordResetSerializer
from .utils import send_eskiz_sms
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
            serializer.save()
            return Response({
                "message": "User created successfully. Please verify your phone number to activate account.",
                "phone_number": serializer.validated_data['phone_number']
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FirebaseVerifyView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = FirebaseVerifySerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            uid = serializer.validated_data['firebase_uid']
            
            try:
                user = User.objects.get(phone_number=phone)
                user.is_verified = True
                user.is_active = True
                user.firebase_uid = uid
                user.save()
                
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    "message": "Login successful",
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    "user": {
                        "phone": user.phone_number,
                        "role": user.role
                    }
                }, status=status.HTTP_200_OK)
            

            except User.DoesNotExist:
                return Response({"error": "User not registered. Please register first."}, status=404)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(phone_number=phone)
                user.set_password(new_password)
                user.is_active = True 
                user.is_verified = True
                user.save()
                
                return Response({
                    "message": "Password has been reset successfully. You can now log in."
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                return Response({"error": "User with this phone number not found."}, status=404)

        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)


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
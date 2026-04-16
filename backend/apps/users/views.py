
import uuid

from django.utils import timezone
from django.db import transaction
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import OtpVerification, User, UserPasswordReset, UserDeviceToken
from .serializers import RegistrationSerializer, PasswordResetConfirmSerializer, CustomTokenObtainPairSerializer, ForgotPasswordSerializer, SendOtpSerializer, RegisterConfirmSerializer,UserDetailSerializer, ChangePhoneSendOtpSerializer, ChangePhoneVerifyOtpSerializer, DeviceTokenRegisterSerializer, DeviceTokenUnregisterSerializer
from .utils import send_sms
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Role


def get_user_by_normalized_phone(phone_number):
    user = User.objects.filter(phone_number=phone_number).first()
    if user:
        return user
    return User.objects.filter(phone_number__endswith=phone_number).first()

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

            is_user_exists = User.objects.filter(phone_number=phone).exists()
            if is_user_exists:
                return Response(
                    {"error": "User with this phone number already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

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

            return Response({"message": "OTP sent successfully.", "is_login": is_login}, status=status.HTTP_200_OK)

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

            user = get_user_by_normalized_phone(phone)
            if not user:
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

            user = get_user_by_normalized_phone(phone)
            if not user:
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


class SendPhoneChangeOtpView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePhoneSendOtpSerializer

    def post(self, request):
        if request.user.role not in [Role.DRIVER, Role.WORKSHOP]:
            return Response(
                {"error": "Only driver and workshop users can change phone number."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            new_phone_number = serializer.validated_data['new_phone_number']

            if new_phone_number == request.user.phone_number:
                return Response(
                    {"error": "New phone number must be different from current phone number."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if User.objects.filter(phone_number=new_phone_number).exclude(pk=request.user.pk).exists():
                return Response(
                    {"error": "User with this phone number already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            otp = send_sms(new_phone_number)
            if otp:
                OtpVerification.objects.update_or_create(
                    phone_number=new_phone_number,
                    defaults={
                        "code": otp,
                        "expires_at": timezone.now() + timezone.timedelta(minutes=5),
                        "attempts": 0,
                        "is_used": False
                    }
                )

            return Response(
                {"message": "OTP sent successfully."},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyPhoneChangeOtpView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePhoneVerifyOtpSerializer

    def post(self, request):
        if request.user.role not in [Role.DRIVER, Role.WORKSHOP]:
            return Response(
                {"error": "Only driver and workshop users can change phone number."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            new_phone_number = serializer.validated_data['new_phone_number']
            code = serializer.validated_data['code']

            if new_phone_number == request.user.phone_number:
                return Response(
                    {"error": "New phone number must be different from current phone number."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if User.objects.filter(phone_number=new_phone_number).exclude(pk=request.user.pk).exists():
                return Response(
                    {"error": "User with this phone number already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            otp_record = OtpVerification.objects.filter(
                phone_number=new_phone_number,
                code=code,
                is_used=False
            ).first()

            if not otp_record or not otp_record.is_valid():
                return Response({"error": "Invalid or expired OTP code."}, status=status.HTTP_400_BAD_REQUEST)

            otp_record.is_used = True
            otp_record.save(update_fields=['is_used'])

            request.user.phone_number = new_phone_number
            request.user.save(update_fields=['phone_number'])

            refresh = RefreshToken.for_user(request.user)

            return Response(
                {
                    "message": "Phone number changed successfully.",
                    "user": UserDetailSerializer(request.user).data,
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    }
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterDeviceTokenView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceTokenRegisterSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        platform = serializer.validated_data['platform']

        with transaction.atomic():
            UserDeviceToken.objects.update_or_create(
                token=token,
                defaults={
                    'user': request.user,
                    'platform': platform,
                    'is_active': True,
                }
            )

        return Response({'message': 'Device token registered successfully.'}, status=status.HTTP_200_OK)


class UnregisterDeviceTokenView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceTokenUnregisterSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        UserDeviceToken.objects.filter(user=request.user, token=token).update(is_active=False)

        return Response({'message': 'Device token unregistered successfully.'}, status=status.HTTP_200_OK)



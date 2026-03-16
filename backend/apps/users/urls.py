from django.urls import path
from .views import (ForgotPasswordView, LoginView, PasswordResetConfirmView, RegisterView, SendOtpView, UserDetailView, VerifyOtpView,VerifyPasswordResetOtpView, DriverProfileUpdateView, WorkshopProfileUpdateView)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'), 
    path('send-otp/', SendOtpView.as_view(), name='send_otp'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify_otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-forgot-password/', VerifyPasswordResetOtpView.as_view(), name='verify_forgot_password'),  # Reusing SendOtpView for password reset
    path('password-reset/', PasswordResetConfirmView.as_view(), name='password_reset'),
    path('profile/', UserDetailView.as_view(), name='profile'),
    path('profile/driver/update/', DriverProfileUpdateView.as_view(), name='driver_profile_update'),
    path('profile/workshop/update/', WorkshopProfileUpdateView.as_view(), name='workshop_profile_update'),
    # path('firebase-verify/', FirebaseVerifyView.as_view(), name='firebase_verify'),
    # path('test-register/', TestRegisterView.as_view(), name='test_register'),
]
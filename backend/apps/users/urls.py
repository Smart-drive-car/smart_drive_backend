from django.urls import path
from .views import (ForgotPasswordView, LoginView, PasswordResetConfirmView, RegisterView, SendOtpView, UserDetailView, VerifyOtpView,VerifyPasswordResetOtpView, SendPhoneChangeOtpView, VerifyPhoneChangeOtpView)
from apps.driver.views import DriverProfileUpdateView
from apps.workshop.views import WorkshopProfileUpdateView, WorkshopListView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('send-otp/', SendOtpView.as_view(), name='send_otp'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify_otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-forgot-password/', VerifyPasswordResetOtpView.as_view(), name='verify_forgot_password'),
    path('password-reset/', PasswordResetConfirmView.as_view(), name='password_reset'),
    path('profile/', UserDetailView.as_view(), name='profile'),
    path('profile/change-phone/send-otp/', SendPhoneChangeOtpView.as_view(), name='profile_change_phone_send_otp'),
    path('profile/change-phone/verify-otp/', VerifyPhoneChangeOtpView.as_view(), name='profile_change_phone_verify_otp'),
    path('workshops/', WorkshopListView.as_view(), name='workshop_list_legacy'),
    path('profile/driver/update/', DriverProfileUpdateView.as_view(), name='driver_profile_update_legacy'),
    path('profile/workshop/update/', WorkshopProfileUpdateView.as_view(), name='workshop_profile_update_legacy'),
    # path('firebase-verify/', FirebaseVerifyView.as_view(), name='firebase_verify'),
    # path('test-register/', TestRegisterView.as_view(), name='test_register'),
]
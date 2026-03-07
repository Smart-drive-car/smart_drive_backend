from django.urls import path
from .views import (FirebaseVerifyView, LoginView, PasswordResetView, RegisterView)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'), 
    path('firebase-verify/', FirebaseVerifyView.as_view(), name='firebase_verify'),
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    # path('test-register/', TestRegisterView.as_view(), name='test_register'),
]
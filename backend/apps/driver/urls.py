from django.urls import path

from .views import DriverProfileUpdateView


urlpatterns = [
    path('profile/update/', DriverProfileUpdateView.as_view(), name='driver_profile_update'),
]

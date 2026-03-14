from django.urls import path
from .views import VehicleCreateView

urlpatterns = [
    path('create/', VehicleCreateView.as_view(), name='vehicle-create'),
]
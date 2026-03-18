from django.urls import path
from .views import VehicleCreateView, VehicleRetrieveUpdateDestroyView

urlpatterns = [
    path('create/', VehicleCreateView.as_view(), name='vehicle-create'),
    path('<int:pk>/', VehicleRetrieveUpdateDestroyView.as_view(), name='vehicle-detail'),
]
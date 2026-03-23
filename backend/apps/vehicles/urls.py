from django.urls import path
from .views import (
    VehicleCreateView,
    VehicleRetrieveUpdateDestroyView,
    VehicleBrandListView,
    VehicleModelListView,
)

urlpatterns = [
    path('brands/', VehicleBrandListView.as_view(), name='vehicle-brand-list'),
    path('models/', VehicleModelListView.as_view(), name='vehicle-model-list'),
    path('create/', VehicleCreateView.as_view(), name='vehicle-create'),
    path('<int:pk>/', VehicleRetrieveUpdateDestroyView.as_view(), name='vehicle-detail'),
]
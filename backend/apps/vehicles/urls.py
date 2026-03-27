from django.urls import path
from .views import (
    VehicleCreateView,
    VehicleRetrieveUpdateDestroyView,
    VehicleBrandListView,
    VehicleModelListView,
    CarSearchView,
    UpdateMileageView,
)

urlpatterns = [
    path('brands/', VehicleBrandListView.as_view(), name='vehicle-brand-list'),
    path('models/', VehicleModelListView.as_view(), name='vehicle-model-list'),
    path('create/', VehicleCreateView.as_view(), name='vehicle-create'),
    path('update-mileage/', UpdateMileageView.as_view(), name='update-mileage'),
    path('<int:pk>/', VehicleRetrieveUpdateDestroyView.as_view(), name='vehicle-detail'),
    path('search/', CarSearchView.as_view(), name='car-search'),
]
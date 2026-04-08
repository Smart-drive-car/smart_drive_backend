from django.contrib import admin

from .models import Car, DriverCar, VehicleBrand, VehicleModel
from import_export import resources
from import_export.admin import ImportExportModelAdmin


@admin.register(DriverCar)
class DriverCarAdmin(ImportExportModelAdmin):
    list_display = ('id', 'driver_profile', 'car',)
    search_fields = ('driver_profile__user__phone_number', 'car__vehicle_model__brand__name', 'car__vehicle_model__model_name')


@admin.register(Car)
class CarAdmin(ImportExportModelAdmin):
    list_display = ('id', 'car_plate_number', 'vehicle_model', 'owner', 'current_mileage')
    search_fields = ('car_plate_number', 'vehicle_model__brand__name', 'vehicle_model__model_name', 'owner__user__phone_number')


@admin.register(VehicleModel)
class VehicleModelAdmin(ImportExportModelAdmin):
    list_display = ('id', 'brand', 'model_name', 'image')
    search_fields = ('brand__name', 'model_name')


@admin.register(VehicleBrand)
class VehicleBrandAdmin(ImportExportModelAdmin):
    list_display = ('id', 'name',)
    search_fields = ('name',)

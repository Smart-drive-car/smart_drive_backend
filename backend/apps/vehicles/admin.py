from django.contrib import admin

from .models import Car, DriverCar, VehicleBrand, VehicleModel, VehicleModel
from import_export import resources
from import_export.admin import ImportExportModelAdmin


@admin.register(DriverCar)
class DriverCarAdmin(ImportExportModelAdmin):
    list_display = ('driver_profile', 'car',)
    search_fields = ('driver_profile__user__username', 'car__make', 'car__model')


@admin.register(Car)
class CarAdmin(ImportExportModelAdmin):
    list_display = ('id', 'car_plate_number', 'vehicle_model', 'current_mileage')
    search_fields = ('car_plate_number', 'vehicle_model__brand', 'vehicle_model__model_name')


@admin.register(VehicleModel)
class VehicleModelAdmin(ImportExportModelAdmin):
    list_display = ('brand', 'model_name', 'image')
    search_fields = ('brand', 'model_name')


@admin.register(VehicleBrand)
class VehicleBrandAdmin(ImportExportModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
from django.contrib import admin

from .models import Car, DriverCar, VehicleBrand, VehicleModel, VehicleModel

@admin.register(DriverCar)
class DriverCarAdmin(admin.ModelAdmin):
    list_display = ('driver_profile', 'car',)
    search_fields = ('driver_profile__user__username', 'car__make', 'car__model')


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('id', 'car_plate_number', 'vehicle_model', 'current_mileage')
    search_fields = ('car_plate_number', 'vehicle_model__brand', 'vehicle_model__model_name')


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model_name', 'image')
    search_fields = ('brand', 'model_name')


@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
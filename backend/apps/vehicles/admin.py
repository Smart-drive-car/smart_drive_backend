from django.contrib import admin

from .models import Car, DriverCar, VehicleModel

@admin.register(DriverCar)
class DriverCarAdmin(admin.ModelAdmin):
    list_display = ('driver_profile', 'car',)
    search_fields = ('driver_profile__user__username', 'car__make', 'car__model')


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('car_plate_number', 'vehicle_model', 'year', 'current_mileage')
    search_fields = ('car_plate_number', 'vehicle_model__brand', 'vehicle_model__model_name')


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model_name')
    search_fields = ('brand', 'model_name')
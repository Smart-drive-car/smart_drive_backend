from django.contrib import admin

from .models import DriverProfile
from apps.vehicles.models import DriverCar

class DriverCarInline(admin.TabularInline):
    model = DriverCar
    extra = 1

@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'created_at')
    search_fields = ('full_name', 'user__phone_number')
    inlines = [DriverCarInline]

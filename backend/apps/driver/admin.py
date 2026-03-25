from django.contrib import admin

from .models import DriverProfile


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'created_at')
    search_fields = ('full_name', 'user__phone_number')

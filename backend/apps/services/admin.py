from django.contrib import admin
from .models import Service, ServiceType
# Register your models here.

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('-created_at',) 

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_type', 'workshop', 'car', 'created_at', 'updated_at')
    search_fields = ('service_type__name', 'workshop__title', 'car__license_plate')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        user = request.user
        
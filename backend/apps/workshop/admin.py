from django.contrib import admin

from .models import WorkshopProfile, WorkshopProfileImages, WorkshopRating


@admin.register(WorkshopProfile)
class WorkshopProfileAdmin(admin.ModelAdmin):
    list_display = ('title', 'working_time', 'description', 'user', 'created_at')
    search_fields = ('title', 'description', 'user__phone_number')


@admin.register(WorkshopProfileImages)
class WorkshopProfileImagesAdmin(admin.ModelAdmin):
    list_display = ('id', 'workshop_profile', 'created_at')
    search_fields = ('workshop_profile__title',)


@admin.register(WorkshopRating)
class WorkshopRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'workshop', 'driver', 'rating', 'created_at')
    search_fields = ('workshop__title', 'driver__full_name')

from django.urls import path

from .views import WorkshopListView, WorkshopProfileUpdateView


urlpatterns = [
    path('', WorkshopListView.as_view(), name='workshop_list'),
    path('profile/update/', WorkshopProfileUpdateView.as_view(), name='workshop_profile_update'),
]

from django.urls import path

from .views import WorkshopListView, WorkshopProfileUpdateView, WorkshopDetailView


urlpatterns = [
    path('search/', WorkshopListView.as_view(), name='workshop_list'),
    path('<int:pk>/', WorkshopDetailView.as_view(), name='workshop_detail'),
    path('profile/update/', WorkshopProfileUpdateView.as_view(), name='workshop_profile_update'),
]

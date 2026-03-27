from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.shared.models import BaseModel
from apps.driver.models import DriverProfile
from apps.users.models import User


class WorkshopProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    working_time = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.user}"

    class Meta:
        db_table = 'users_workshopprofile'


class WorkshopProfileImages(BaseModel):
    workshop_profile = models.ForeignKey(WorkshopProfile, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='workshop_profiles/')

    def __str__(self):
        return f"Image for {self.workshop_profile}"

    class Meta:
        db_table = 'users_workshopprofileimages'


class WorkshopRating(BaseModel):
    workshop = models.ForeignKey(WorkshopProfile, on_delete=models.CASCADE, related_name='ratings')
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='workshop_ratings')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    def __str__(self):
        return f"{self.workshop.title} - {self.driver.full_name}: {self.rating}"

    class Meta:
        unique_together = ('workshop', 'driver')

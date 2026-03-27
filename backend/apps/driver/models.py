from django.db import models

from apps.shared.models import BaseModel
from apps.users.models import User


class DriverProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='driver_profiles/', null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} - {self.user}"

    class Meta:
        db_table = 'users_driverprofile'

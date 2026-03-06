from django.db import models
from pytz import timezone
from apps.shared.models import BaseModel
from apps.users.models import DriverProfile, User


class Vehicle(BaseModel):
    license_plate = models.CharField(max_length=20, unique=True)
    mileage = models.IntegerField()
    car_model = models.CharField(max_length=255)
    year = models.IntegerField()

    def __str__(self):
        return f"({self.license_plate}) {self.car_model}"
    

class DriverVehicle(BaseModel):
    driver_profile = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='vehicles')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.driver_profile} - {self.vehicle}"
    
    class Meta:
        unique_together = ('driver_profile', 'vehicle')


class AdminProfile(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    full_name  = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.full_name
    


class OtpCode(models.Model):
    phone      = models.CharField(max_length=15, db_index=True)
    code       = models.CharField(max_length=6)
    is_used    = models.BooleanField(default=False)
    attempts   = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_codes"
        ordering = ["-created_at"]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired() and self.attempts < 3

    def __str__(self):
        return f"{self.phone} — {self.code} ({'used' if self.is_used else 'active'})"
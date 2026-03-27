from django.db import models
from pytz import timezone
from apps.shared.models import BaseModel
from apps.driver.models import DriverProfile


class VehicleBrand(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class VehicleModel(BaseModel):
    """Example: Chevrolet, Gentra, Nexia 3"""
    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='vehicle_models/', null=True, blank=True)

    def __str__(self):
        return f"{self.brand} {self.model_name}"

class Car(BaseModel):
    owner = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='owned_cars', null=True, blank=True)
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.SET_NULL, null=True)
    car_plate_number = models.CharField(max_length=20, unique=True)
    released_year = models.PositiveIntegerField(null=True, blank=True)
    current_mileage = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.car_plate_number} ({self.vehicle_model})"

    class Meta:
        unique_together = ('owner', 'car_plate_number')

class DriverCar(BaseModel):
    driver_profile = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='vehicles')
    car = models.ForeignKey(Car, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.driver_profile} - {self.car}"
    
    class Meta:
        unique_together = ('driver_profile', 'car')



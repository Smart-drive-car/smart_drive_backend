from django.db import models
from apps.shared.models import BaseModel
from apps.vehicles.models import Car
from apps.workshop.models import WorkshopProfile


class ServiceType(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    owner = models.ForeignKey(
        'workshop.WorkshopProfile',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='service_types'
    )

    def __str__(self):
        return self.name


class Service(BaseModel):
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
    workshop = models.ForeignKey(WorkshopProfile, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    probeg = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.service_type.name} for {self.car} at {self.workshop.title}"
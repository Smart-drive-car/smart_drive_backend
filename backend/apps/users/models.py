from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator
from apps.shared.models import BaseModel

class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None):
        if not phone_number:
            raise ValueError('Users must have a phone number')

        user = self.model(
            phone_number=phone_number,
        )
        
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None):
        user = self.create_user(
            phone_number,
            password=password,
        )
        user.save(using=self._db)
        return user


class Role(models.TextChoices):
        DRIVER = 'DRIVER', 'Driver'
        WORKSHOP = 'WORKSHOP', 'Workshop'
        ADMIN = 'ADMIN', 'Admin'

class User(AbstractBaseUser, BaseModel):
    phone_regex = RegexValidator(
        regex=r'^\d{9}$', 
        message="Phone number must be entered in the format: '993335566'. Up to 9 digits allowed."
    )
    phone_number = models.CharField(max_length=20, unique=True, validators=[phone_regex])
    is_active = models.BooleanField(default=True)
    objects = UserManager()
    role = models.CharField(max_length=20, choices=Role.choices)

    USERNAME_FIELD = 'phone_number'

    def __str__(self):
        return self.phone_number
    

class DriverProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='driver_profiles/')


    def __str__(self):
        return f"{self.full_name} - {self.user}"

    

class WorkshopProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    address = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.title} - {self.user}"
    
class WorkshopProfileImages(BaseModel):
    workshop_profile = models.ForeignKey(WorkshopProfile, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='workshop_profiles/')

    def __str__(self):
        return f"Image for {self.workshop_profile}"


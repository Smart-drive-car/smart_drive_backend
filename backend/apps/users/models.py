from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from apps.shared.models import BaseModel
from django.utils import timezone
import uuid

class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Users must have a phone number')

        user = self.model(
            phone_number=phone_number,
            **extra_fields
        )
        
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None,**extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN') # Set the role to ADMIN automatically

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)


class Role(models.TextChoices):
        DRIVER = 'DRIVER', 'Driver'
        WORKSHOP = 'WORKSHOP', 'Workshop'
        ADMIN = 'ADMIN', 'Admin'

class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    phone_regex = RegexValidator(
        regex=r'^\d{9}$', 
        message="Phone number must be entered in the format: '993335566'. Up to 9 digits allowed."
    )
    phone_number = models.CharField(max_length=20, unique=True, validators=[phone_regex])
    role = models.CharField(max_length=20, choices=Role.choices)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()
    
    USERNAME_FIELD = 'phone_number'

    def __str__(self):
        return self.phone_number
    
    class Meta:
        ordering = ['-created_at']
    


class AdminProfile(BaseModel):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    full_name  = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.full_name
    
def get_otp_expiry():
    return timezone.now() + timezone.timedelta(minutes=5)

class OtpVerification(BaseModel):
    phone_number = models.CharField(max_length=20)
    code         = models.CharField(max_length=6)
    is_used      = models.BooleanField(default=False)
    attempts     = models.PositiveSmallIntegerField(default=0)
    expires_at   = models.DateTimeField(default=get_otp_expiry)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_verifications"
        ordering = ["-created_at"]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired() and self.attempts < 3

    def __str__(self):
        return f"{self.phone_number} — {self.code} ({'used' if self.is_used else 'active'})"



class UserPasswordReset(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='password_reset')
    reset_token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        return self.created_at > timezone.now() - timezone.timedelta(minutes=15)
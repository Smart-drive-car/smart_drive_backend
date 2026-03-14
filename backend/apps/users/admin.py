from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import User, DriverProfile, WorkshopProfile, AdminProfile, OtpVerification

# 1. THE CREATION FORM
class MyUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('phone_number','role') # ONLY use fields that actually exist in your model

    def clean_password_confirm(self):
        p1 = self.cleaned_data.get("password")
        p2 = self.cleaned_data.get("password_confirm")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords don't match")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"]) # Hashing
        if commit:
            user.save()
        return user

# 2. THE CHANGE FORM
class MyUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = '__all__'

# 3. THE ADMIN CLASS
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = MyUserChangeForm
    add_form = MyUserCreationForm

    # Which columns show up in the table view
    list_display = ('phone_number', 'is_staff',)
    list_filter = ('is_staff',)
    
    # Crucial: Override ordering to use phone_number
    ordering = ('phone_number',)
    search_fields = ('phone_number',)

    # The layout for the EDIT page
    fieldsets = (
        (None, {'fields': ('phone_number','role', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser')}),
    )

    # The layout for the ADD page
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'role', 'password', 'password_confirm'),
        }),
    )

    filter_horizontal = ()


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'created_at')
    search_fields = ('full_name', 'user__phone_number')

@admin.register(WorkshopProfile)
class WorkshopProfileAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    search_fields = ('title', 'user__phone_number')

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'created_at')
    search_fields = ('full_name', 'user__phone_number')

@admin.register(OtpVerification)
class OtpVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'code', 'is_used', 'expires_at', 'created_at')
    search_fields = ('phone_number',)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Trip, Booking, PhoneOTP

# This tells Django how to display your Custom User
class CustomUserAdmin(UserAdmin):
    model = User
    
    # 1. CONTROL WHICH COLUMNS APPEAR IN THE LIST
    list_display = ['phone_number', 'username', 'role', 'is_verified', 'date_joined']
    
    # 2. CONTROL WHICH FIELDS APPEAR WHEN YOU CLICK A USER
    # We are adding a new section called "Driver Documents & Info"
    fieldsets = UserAdmin.fieldsets + (
        ('Driver Details', {
            'fields': (
                'role', 
                'is_verified', 
                'license_number', 
                'vehicle_number', 
                'vehicle_type',
                # Add your exact image field names here if they are different:
                # 'license_image', 
                # 'vehicle_image',
            )
        }),
    )

# Register the models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Trip)
admin.site.register(Booking)
admin.site.register(PhoneOTP)
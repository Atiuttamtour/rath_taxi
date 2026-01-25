from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Trip, Booking, PhoneOTP

# This tells Django how to display your Custom User
class CustomUserAdmin(UserAdmin):
    model = User
    
    # 1. CONTROL WHICH COLUMNS APPEAR IN THE LIST (The Table View)
    list_display = ['phone_number', 'username', 'role', 'is_verified', 'vehicle_number']
    
    # 2. CONTROL WHICH FIELDS APPEAR WHEN YOU CLICK A USER (The Form View)
    # We are adding a new section called "Driver Documents & Info"
    fieldsets = UserAdmin.fieldsets + (
        ('Driver Details', {
            'fields': (
                'role', 
                'is_verified', 
                'address',           # Added Address
                'license_number', 
                'vehicle_number', 
                'vehicle_type',
                
                # 🚀 PROFESSIONAL FIX: IMAGES ARE NOW VISIBLE
                'profile_photo', 
                'license_photo',
                'rc_photo',          # Added RC
                'aadhaar_photo',     # Added Aadhaar
            )
        }),
    )

# Register the models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Trip)
admin.site.register(Booking)
admin.site.register(PhoneOTP)
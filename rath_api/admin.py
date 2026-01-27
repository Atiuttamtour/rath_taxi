from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import mark_safe 
from .models import User, Trip, Booking, EmailOTP 

# ============================================
# 1. EMAIL OTP ADMIN (Make this visible!)
# ============================================
@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    # This ensures you see the Email, The Code, and Time Created
    list_display = ('email', 'otp_code', 'created_at')
    search_fields = ('email',)
    ordering = ('-created_at',) # Shows newest OTPs at the top

# ============================================
# 2. CUSTOM USER ADMIN (With Image Previews)
# ============================================
class CustomUserAdmin(UserAdmin):
    model = User
    
    # --- Image Preview Functions ---
    def profile_preview(self, obj):
        if obj.profile_photo:
            # 🚀 Shows a small circle image
            return mark_safe(f'<img src="{obj.profile_photo.url}" width="50" height="50" style="border-radius:50px; object-fit:cover;" />')
        return "No Image"
    profile_preview.short_description = "Photo"

    def license_preview(self, obj):
        if obj.license_photo:
            # 🚀 Shows a rectangle image
            return mark_safe(f'<img src="{obj.license_photo.url}" width="100" height="60" style="border-radius:5px; object-fit:cover;" />')
        return "No License"
    license_preview.short_description = "License"

    # --- What to show in the Main List ---
    list_display = ['email', 'profile_preview', 'role', 'is_verified', 'phone_number']
    list_filter = ('role', 'is_verified') # Adds a sidebar filter
    
    # --- What to show in the Edit Form ---
    fieldsets = UserAdmin.fieldsets + (
        ('Driver Documents', {
            'fields': (
                'role', 
                'is_verified',
                'phone_number',
                'address',
                'vehicle_number',
                'vehicle_type',
                # Display both the file upload AND the preview
                'profile_photo', 'profile_preview',
                'license_photo', 'license_preview',
                'rc_photo',
                'aadhaar_photo',
            )
        }),
    )
    # Read-only previews so you can't edit the "image view" itself
    readonly_fields = ['profile_preview', 'license_preview']

# Register Models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Trip)
admin.site.register(Booking)
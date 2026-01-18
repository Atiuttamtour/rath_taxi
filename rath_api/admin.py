from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, DriverProfile, Trip, Booking  # <--- Added Booking

# 1. User Admin (Login accounts)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone_number', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Details', {'fields': ('phone_number', 'role', 'profile_photo')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('email', 'phone_number', 'role')}),
    )

# 2. Trip Admin (To see routes clearly)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'driver_name', 'source_city', 'destination_city', 'price_per_seat', 'available_seats', 'status')
    
    def driver_name(self, obj):
        return obj.driver.user.username

# 3. Booking Admin (To see Tickets)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'trip_info', 'customer_name', 'seats_booked', 'total_cost', 'status')

    def trip_info(self, obj):
        return f"{obj.trip.source_city} -> {obj.trip.destination_city}"

    def customer_name(self, obj):
        return obj.customer.username

# Register everything
admin.site.register(User, CustomUserAdmin)
admin.site.register(DriverProfile)
admin.site.register(Trip, TripAdmin)
admin.site.register(Booking, BookingAdmin) # <--- NOW YOU CAN SEE IT!
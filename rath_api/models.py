from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# ==========================================
# 1. CUSTOM USER
# Handles Login for both Drivers & Customers
# ==========================================
class User(AbstractUser):
    IS_DRIVER = 'DRIVER'
    IS_CUSTOMER = 'CUSTOMER'
    IS_AGENT = 'AGENT'
    
    ROLE_CHOICES = [
        (IS_DRIVER, 'Driver'),
        (IS_CUSTOMER, 'Customer'),
        (IS_AGENT, 'Agent'),
    ]
    
    # Standard Fields
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=IS_CUSTOMER)
    phone_number = models.CharField(max_length=15, unique=True)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)

    # --- FIX: ADDED SECURITY FIELDS DIRECTLY TO USER ---
    # This fixes "AttributeError: User object has no attribute is_verified"
    is_verified = models.BooleanField(default=False) 
    license_number = models.CharField(max_length=50, null=True, blank=True)

    # Fix for Django's default related_name conflict
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='rath_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='rath_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return f"{self.username} ({self.role})"


# ==========================================
# 2. DRIVER PROFILE (OPTIONAL/ADVANCED)
# We keep this for extra data (Bank details, etc.)
# ==========================================
class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    
    # Additional Details
    vehicle_number = models.CharField(max_length=50, null=True, blank=True)
    aadhaar_number = models.CharField(max_length=50, null=True, blank=True)
    
    # Wallet Logic
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    pending_dues = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    last_due_date = models.DateTimeField(null=True, blank=True)
    
    is_blocked = models.BooleanField(default=False) 

    def __str__(self):
        return f"Driver Profile: {self.user.username}"


# ==========================================
# 3. THE TRIP
# The Core "Empty Leg" Feature
# ==========================================
class Trip(models.Model):
    # --- FIX: LINKED DIRECTLY TO USER ---
    # This prevents errors when creating trips in views.py
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')
    
    source_city = models.CharField(max_length=100) 
    destination_city = models.CharField(max_length=100)
    
    # Coordinates
    source_lat = models.FloatField()
    source_lng = models.FloatField()
    dest_lat = models.FloatField()
    dest_lng = models.FloatField()
    
    start_time = models.DateTimeField()
    available_seats = models.IntegerField(default=3)
    
    # Pricing & Status
    price_per_seat = models.DecimalField(max_digits=10, decimal_places=2)
    is_full_car_booking = models.BooleanField(default=False)
    
    status = models.CharField(max_length=20, default='SCHEDULED') 

    def __str__(self):
        return f"{self.source_city} -> {self.destination_city} ({self.status})"


# ==========================================
# 4. THE BOOKING
# The Ticket Logic
# ==========================================
class Booking(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='bookings')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booked_trips')
    
    seats_booked = models.IntegerField(default=1)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    booking_date = models.DateTimeField(default=timezone.now)
    
    STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='CONFIRMED')

    def __str__(self):
        return f"Ticket #{self.id} - {self.customer.username}"
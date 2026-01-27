from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# ==========================================
# 1. CUSTOM USER
# Handles Login for both Drivers & Customers
# ==========================================
class User(AbstractUser):
    # Role choices
    CUSTOMER = 'CUSTOMER'
    DRIVER = 'DRIVER'
    AGENT = 'AGENT'
    ROLE_CHOICES = [
        (CUSTOMER, 'Customer'),
        (DRIVER, 'Driver'),
        (AGENT, 'Agent'),
    ]
    
    # 🚀 UPDATE: Email is now the main login ID
    email = models.EmailField(unique=True) 
    
    # 🚀 UPDATE: Phone is now optional (so we can sign up with email first)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CUSTOMER)
    
    # --- SECURITY & VERIFICATION ---
    is_verified = models.BooleanField(default=False)
    
    # --- DRIVER SPECIFIC FIELDS ---
    address = models.TextField(blank=True, null=True) 
    
    license_number = models.CharField(max_length=50, blank=True, null=True)
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    vehicle_type = models.CharField(max_length=20, blank=True, null=True)

    # 🚀 DOCUMENT STORAGE (IMAGES)
    profile_photo = models.ImageField(upload_to='drivers/profile/', null=True, blank=True)
    license_photo = models.ImageField(upload_to='drivers/license/', null=True, blank=True)
    rc_photo = models.ImageField(upload_to='drivers/rc/', null=True, blank=True)
    aadhaar_photo = models.ImageField(upload_to='drivers/aadhaar/', null=True, blank=True)

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

    # We use Email to log in now, not username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.role})"


# ==========================================
# 2. DRIVER PROFILE (OPTIONAL)
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
# 3. THE TRIP (Empty Leg)
# ==========================================
class Trip(models.Model):
    # If Driver account is deleted, delete their trips
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')
    
    source_city = models.CharField(max_length=100) 
    destination_city = models.CharField(max_length=100)
    
    # Coordinates
    source_lat = models.FloatField()
    source_lng = models.FloatField()
    dest_lat = models.FloatField()
    dest_lng = models.FloatField()
    
    start_time = models.DateTimeField()
    
    # 🚀 ZERO DECREMENT LOGIC:
    available_seats = models.IntegerField(default=3)
    
    price_per_seat = models.DecimalField(max_digits=10, decimal_places=2)
    is_full_car_booking = models.BooleanField(default=False)
    
    status = models.CharField(max_length=20, default='SCHEDULED') 

    def __str__(self):
        return f"{self.source_city} -> {self.destination_city} ({self.status})"


# ==========================================
# 4. THE BOOKING (The Bridge)
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
        return f"Ticket #{self.id} - {self.customer.email}"


# ==========================================
# 5. SECURITY (EMAIL OTP STORAGE)
# ==========================================
class EmailOTP(models.Model):
    email = models.EmailField(unique=True)  # Changed from Phone to Email
    otp_code = models.CharField(max_length=6)
    count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email} - {self.otp_code}"
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from .models import Trip, User, Booking, PhoneOTP 
import json
import math
import random 

# --- IMPORTS FOR API ---
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# ==========================================
# 1. AUTHENTICATION & SECURITY (OTP SYSTEM)
# ==========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """
    STEP 1: Generates 4-digit OTP.
    - Saves it to Database.
    - Prints to Console (simulating SMS for now).
    """
    phone = request.data.get('phone')
    if not phone:
        return Response({"error": "Phone number required"}, status=400)

    # Generate random 4-digit code
    otp = str(random.randint(1000, 9999))
    
    # Save or Update OTP in Database
    obj, created = PhoneOTP.objects.get_or_create(phone_number=phone)
    obj.otp_code = otp
    obj.save()

    # LOGGING: Print to console so you can see it in Render Logs
    print(f" SECURITY ALERT: OTP for {phone} is {otp}")
    
    return Response({
        "status": "success", 
        "message": "OTP Sent Successfully",
        "debug_otp": otp # For testing purposes only
    })

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    STEP 2: Verifies the code.
    - If Correct: Returns User Data (Login) OR "New User" signal.
    """
    phone = request.data.get('phone')
    otp = request.data.get('otp')

    try:
        otp_record = PhoneOTP.objects.get(phone_number=phone)
        
        if otp_record.otp_code == otp:
            # Code is Correct!
            otp_record.delete() # Security: Delete used OTP
            
            # Now check if this is an Existing User or New User
            try:
                user = User.objects.get(phone_number=phone)
                return Response({
                    "status": "success",
                    "exists": True,
                    "role": user.role,
                    "name": user.first_name,
                    "user_id": user.id,
                    "is_verified": user.is_verified
                })
            except User.DoesNotExist:
                # Phone verified, but user needs to fill Name/Email
                return Response({"status": "success", "exists": False})
        else:
            return Response({"error": "Invalid OTP Code"}, status=400)
            
    except PhoneOTP.DoesNotExist:
        return Response({"error": "Please request a new OTP"}, status=400)

# ==========================================
# 2. USER MANAGEMENT (SMART SIGNUP & PROFILE)
# ==========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def check_phone(request):
    """(Legacy Check - Kept for backup)"""
    phone = request.data.get('phone')
    try:
        user = User.objects.get(phone_number=phone)
        return Response({
            "exists": True, 
            "role": user.role, 
            "name": user.first_name,
            "user_id": user.id,
            "is_verified": user.is_verified 
        })
    except User.DoesNotExist:
        return Response({"exists": False})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def signup_customer(request):
    """Registers a new Passenger (Auto-Verified)"""
    data = request.data
    try:
        # 🚀 FIX: Use get_or_create to update existing users who might have missed the name step
        user, created = User.objects.get_or_create(
            phone_number=data['phone']
        )
        # Update details regardless of whether they are new or existing
        user.first_name = data['name']
        user.email = data.get('email', '')
        user.role = 'customer'
        user.is_verified = True
        user.save()
        
        return Response({"status": "success", "user_id": user.id, "role": "customer"})
    except Exception as e:
        return Response({"status": "error", "message": str(e)})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def signup_driver(request):
    """
    SMART SIGNUP: 
    - Handles New Drivers.
    - Handles Customers UPGRADING to Drivers.
    """
    data = request.data
    try:
        # Try to find existing user (e.g. Customer) or Create New
        user, created = User.objects.get_or_create(
            phone_number=data['phone'],
            defaults={
                'first_name': data['fullName'],
                'role': 'driver',
                'license_number': data.get('vehicleNumber', ''),
                'is_verified': False
            }
        )

        if not created:
            # If user already existed (as Customer), UPGRADE them now
            user.role = 'driver'
            user.first_name = data['fullName'] # Update name
            user.license_number = data.get('vehicleNumber', '')
            user.is_verified = False # Reset verification for security
            user.save()

        return Response({"status": "success", "user_id": user.id, "role": "driver"})
    except Exception as e:
        return Response({"status": "error", "message": str(e)})

# 🚀 NEW API: Get Full Profile (Fixes the missing name in frontend)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_profile(request):
    phone = request.GET.get('phone')
    try:
        user = User.objects.get(phone_number=phone)
        return JsonResponse({
            "status": "success",
            "name": user.first_name,
            "email": user.email,
            "phone": user.phone_number,
            "role": user.role,
            "vehicle_number": user.license_number if user.role == 'driver' else ""
        })
    except User.DoesNotExist:
        return JsonResponse({"status": "error", "message": "User not found"}, status=404)

# ==========================================
# 3. THE MATH SECTION (Rubber Band Logic)
# ==========================================

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculates distance between two GPS points.
    Kept for future use when Maps API is enabled.
    """
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_on_the_way(trip_source, trip_dest, customer_pickup, customer_drop):
    """
    Checks if a customer is roughly on the driver's route.
    Safe-guarded to return TRUE if coordinates are missing (0.0).
    """
    # If coordinates are missing (0.0), skip math and return True (allow city matching)
    if trip_source['lat'] == 0.0 or trip_dest['lat'] == 0.0:
        return True

    total_route = haversine(trip_source['lat'], trip_source['lng'], trip_dest['lat'], trip_dest['lng'])
    leg1 = haversine(trip_source['lat'], trip_source['lng'], customer_pickup['lat'], customer_pickup['lng'])
    leg2 = haversine(customer_pickup['lat'], customer_pickup['lng'], trip_dest['lat'], trip_dest['lng'])
    
    # Allow 10% detour
    if total_route == 0: return True # Avoid division by zero
    
    detour_percentage = ((leg1 + leg2) - total_route) / total_route
    return detour_percentage < 0.1

# ==========================================
# 4. TRIP MANAGEMENT APIs
# ==========================================

@csrf_exempt
def create_trip(request):
    """Only allows VERIFIED drivers to post trips."""
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            driver_user = User.objects.get(phone_number=data['driver_phone'])
            
            # SECURITY BLOCK: If Admin hasn't approved
            if not driver_user.is_verified:
                 return JsonResponse({
                     'error': 'Account Under Review. Please wait for Admin approval.'
                 }, status=403)
                 
        except User.DoesNotExist:
            return JsonResponse({'error': 'Driver not found'}, status=404)

        # 🚀 LOGIC UPDATE: Use .get() with default 0.0 to prevent Crash when Map API is off
        new_trip = Trip.objects.create(
            driver=driver_user, 
            source_city=data['source_city'],
            destination_city=data['destination_city'],
            source_lat=data.get('source_lat', 0.0), # Default to 0.0
            source_lng=data.get('source_lng', 0.0), # Default to 0.0
            dest_lat=data.get('dest_lat', 0.0),     # Default to 0.0
            dest_lng=data.get('dest_lng', 0.0),     # Default to 0.0
            start_time=timezone.now(),
            price_per_seat=data['price'],
            available_seats=data['seats'],
            status='SCHEDULED'
        )
        return JsonResponse({'status': 'success', 'message': 'Trip Created!', 'trip_id': new_trip.id})

# 🚀 SMART DELETE: Ignores spaces and +91 to ensure it works
@csrf_exempt
def delete_trip(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print(f"🛑 DELETE ATTEMPT: Trip {data.get('trip_id')} | Request Phone: {data.get('driver_phone')}")
        
        try:
            trip = Trip.objects.get(id=data['trip_id'])
            
            # CLEAN UP PHONE NUMBERS BEFORE COMPARING
            db_phone = str(trip.driver.phone_number).replace(" ", "").replace("+91", "").strip()
            req_phone = str(data['driver_phone']).replace(" ", "").replace("+91", "").strip()
            
            print(f"🔍 COMPARING: DB({db_phone}) == REQ({req_phone})")

            if db_phone == req_phone:
                trip.delete()
                print("✅ SUCCESS: Trip Deleted")
                return JsonResponse({'status': 'success', 'message': 'Route Deleted'})
            else:
                print("❌ FAILED: Phone mismatch")
                return JsonResponse({'error': 'Unauthorized: Phone mismatch'}, status=403)
        except Trip.DoesNotExist:
            print("❌ FAILED: Trip ID not found")
            return JsonResponse({'error': 'Trip not found'}, status=404)

def get_driver_trips(request):
    """
    Fetches all active trips for a specific driver.
    """
    phone = request.GET.get('phone')
    try:
        driver = User.objects.get(phone_number=phone)
        
        # 🚀 LOGIC: Only show trips created in the last 24 hours
        time_threshold = timezone.now() - timedelta(hours=24)
        
        trips = Trip.objects.filter(driver=driver, status='SCHEDULED', start_time__gte=time_threshold)
        
        results = []
        for t in trips:
            results.append({
                'id': t.id,
                'source': t.source_city,
                'destination': t.destination_city,
                'seats': t.available_seats,
                'price': t.price_per_seat
            })
        return JsonResponse({'status': 'success', 'trips': results})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'})

def search_trips(request):
    """
    🚀 COMBINED LOGIC: 
    1. Checks City Name (Text Match).
    2. Checks GPS Radius (Math) IF coordinates exist.
    3. Hides Full Cars.
    4. Hides Expired Trips.
    """
    s_city = request.GET.get('source_city')
    d_city = request.GET.get('destination_city')
    
    # Optional GPS filtering (for future use)
    pickup_lat = float(request.GET.get('lat', 0.0))
    pickup_lng = float(request.GET.get('lng', 0.0))

    # 1. Base Filter: Start with SCHEDULED trips
    time_threshold = timezone.now() - timedelta(hours=24)
    trips = Trip.objects.filter(
        status='SCHEDULED',
        available_seats__gt=0, 
        start_time__gte=time_threshold
    )

    # 2. Filter by City Name (Primary Method for now)
    if s_city:
        trips = trips.filter(source_city__iexact=s_city)
    if d_city:
        trips = trips.filter(destination_city__iexact=d_city)

    results = []
    for trip in trips:
        # 3. GPS Safety Check 
        driver_source = {'lat': trip.source_lat, 'lng': trip.source_lng}
        driver_dest = {'lat': trip.dest_lat, 'lng': trip.dest_lng}
        customer_loc = {'lat': pickup_lat, 'lng': pickup_lng}
        
        if is_on_the_way(driver_source, driver_dest, customer_loc, driver_dest):
            results.append({
                'driver_name': trip.driver.first_name,
                'vehicle': trip.driver.license_number, 
                'price': trip.price_per_seat,
                'source': trip.source_city,
                'destination': trip.destination_city,
                'trip_id': trip.id,
                'seats_left': trip.available_seats 
            })
            
    return JsonResponse({'status': 'success', 'trips': results, 'count': len(results)})

# ==========================================
# 5. BOOKING APIs
# ==========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def book_seat(request):
    """
    Increments the Booking table.
    🚀 UPDATE: Infinite Booking (Does NOT decrease seats).
    🚀 UPDATE: Returns Driver Contact Details for Popup.
    """
    data = request.data
    try:
        trip = Trip.objects.get(id=data['trip_id'])
        # Try to find user by ID or Phone for flexibility
        user_id = data.get('user_id')
        user_phone = data.get('phone')
        
        if user_id:
            customer = User.objects.get(id=user_id)
        else:
            customer = User.objects.get(phone_number=user_phone)
            
        seats_wanted = int(data.get('seats', 1))
        
        # 🚀 REMOVED: trip.available_seats < seats_wanted check
        # We allow booking even if "technically" full, per your request.
            
        cost = float(trip.price_per_seat) * seats_wanted
        
        booking = Booking.objects.create(
            trip=trip,
            customer=customer,
            seats_booked=seats_wanted,
            total_cost=cost,
            status='CONFIRMED'
        )
        
        # 🚀 REMOVED: trip.available_seats -= seats_wanted
        
        return Response({
            'status': 'success',
            'message': 'Booking Confirmed!', 
            'ticket_id': booking.id,
            'remaining_seats': trip.available_seats,
            # 🚀 NEW: Send Driver Details for Popup
            'driver_details': {
                'name': trip.driver.first_name,
                'phone': trip.driver.phone_number,
                'vehicle': trip.driver.license_number
            }
        })
    except (Trip.DoesNotExist, User.DoesNotExist):
        return Response({'status': 'error', 'message': 'Trip or Customer not found'}, status=404)

# 🚀 NEW INCREMENT: Passenger View - See my history
@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_bookings(request):
    """
    Fetches all tickets for a specific passenger.
    """
    phone = request.GET.get('phone')
    try:
        customer = User.objects.get(phone_number=phone)
        bookings = Booking.objects.filter(customer=customer).order_by('-booking_date')
        
        data = []
        for b in bookings:
            data.append({
                'id': b.id,
                'source': b.trip.source_city,
                'destination': b.trip.destination_city,
                'seats': b.seats_booked,
                'total_cost': b.total_cost,
                'driver': b.trip.driver.first_name,
                'status': b.status,
                'date': b.booking_date.strftime("%d %b, %H:%M")
            })
        return JsonResponse({'status': 'success', 'bookings': data})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'})

def get_trip_bookings(request):
    trip_id = request.GET.get('trip_id')
    try:
        trip = Trip.objects.get(id=trip_id)
        bookings = trip.bookings.all()
        
        data = []
        for b in bookings:
            data.append({
                'customer': b.customer.first_name,
                'seats': b.seats_booked,
                'revenue': b.total_cost,
                'status': b.status
            })
        return JsonResponse({'bookings': data})
    except Trip.DoesNotExist:
        return JsonResponse({'bookings': []})

@api_view(['GET'])
@permission_classes([AllowAny])
def get_trip_passengers(request):
    """
    Retrieves Name, Phone, and Seats for everyone who booked a specific trip.
    Security: Only the trip owner can see this.
    """
    trip_id = request.GET.get('trip_id')
    phone = request.GET.get('phone')
    
    try:
        # Verify the trip belongs to the requesting driver
        trip = Trip.objects.get(id=trip_id, driver__phone_number=phone)
        bookings = Booking.objects.filter(trip=trip)
        
        passengers = []
        for b in bookings:
            passengers.append({
                "name": b.customer.first_name,
                "phone": b.customer.phone_number,
                "seats": b.seats_booked,
                "status": b.status
            })
            
        return JsonResponse({"status": "success", "passengers": passengers})
    except Trip.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Trip not found or unauthorized"}, status=404)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from .models import Trip, User, Booking, PhoneOTP 
import json
import math
import random 

# --- IMPORTS FOR API ---
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

# ==========================================
# 1. AUTHENTICATION & SECURITY (OTP SYSTEM)
# ==========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    phone = request.data.get('phone')
    if not phone:
        return Response({"error": "Phone number required"}, status=400)

    otp = str(random.randint(1000, 9999))
    obj, created = PhoneOTP.objects.get_or_create(phone_number=phone)
    obj.otp_code = otp
    obj.save()

    print(f" SECURITY ALERT: OTP for {phone} is {otp}")
    return Response({"status": "success", "message": "OTP Sent Successfully", "debug_otp": otp})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    phone = request.data.get('phone')
    otp = request.data.get('otp')

    try:
        otp_record = PhoneOTP.objects.get(phone_number=phone)
        if otp_record.otp_code == otp:
            otp_record.delete() # OTP is single-use
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
    """
    Checks if a user exists to route them to Login or Signup.
    """
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
    data = request.data
    try:
        if not data.get('phone') or not data.get('name'):
             return Response({"status": "error", "message": "Phone and Name are required"}, status=400)

        phone = data['phone']
        email = data.get('email', '').strip()

        # 🛡️ SECURITY FIX: Check if email is already taken by a DIFFERENT phone number
        if email and User.objects.filter(email=email).exclude(phone_number=phone).exists():
            return Response({"status": "error", "message": "This email is already in use by another account."}, status=400)

        # 🚀 SMART UPDATE: If user exists (maybe dropped off halfway), update them.
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={'username': phone} 
        )
        
        user.first_name = data['name']
        if email: user.email = email
        user.role = 'customer'
        user.is_verified = True # Customers don't need doc verification
        user.save()
        
        return Response({"status": "success", "user_id": user.id, "role": "customer"})
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def signup_driver(request):
    """
    SMART SIGNUP (PROFESSIONAL): 
    - Handles Document Uploads.
    - 🚀 BUG FIX: Successfully upgrades a 'Customer' to a 'Driver' without crashing.
    """
    data = request.data
    try:
        # 1. Extract Data
        phone = data.get('phone')
        full_name = data.get('fullName')
        email = data.get('email', '').strip()
        address = data.get('address', '')
        vehicle_number = data.get('vehicle_number')
        vehicle_type = data.get('vehicle_type', 'Sedan') 

        if not phone:
            return Response({"status": "error", "message": "Phone number is missing"}, status=400)

        # 🛡️ SECURITY FIX: Check if email is already taken by a DIFFERENT phone number
        if email and User.objects.filter(email=email).exclude(phone_number=phone).exists():
            return Response({"status": "error", "message": "This email is already in use by another driver."}, status=400)

        # 2. Get or Create User (This handles the "Account Upgrade" scenario)
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={
                'username': phone, 
                'first_name': full_name,
                'email': email,
                'role': 'driver',
                'is_verified': False, 
                'vehicle_number': vehicle_number,
                'vehicle_type': vehicle_type,
                'address': address
            }
        )

        # 3. FORCE UPDATE: Even if user existed as Customer, make them Driver now
        user.role = 'driver'
        user.username = phone # Ensure unique constraint is met
        
        if full_name: user.first_name = full_name
        if email: user.email = email
        if vehicle_number: user.vehicle_number = vehicle_number
        if vehicle_type: user.vehicle_type = vehicle_type
        if address: user.address = address
        
        # Reset verification because they are uploading NEW documents
        user.is_verified = False 
        
        # 4. Handle Images (Only update if new files provided)
        if 'profile_photo' in request.FILES: user.profile_photo = request.FILES['profile_photo']
        if 'license_photo' in request.FILES: user.license_photo = request.FILES['license_photo']
        if 'rc_photo' in request.FILES: user.rc_photo = request.FILES['rc_photo']
        if 'aadhaar_photo' in request.FILES: user.aadhaar_photo = request.FILES['aadhaar_photo']

        user.save()

        return Response({"status": "success", "user_id": user.id, "role": "driver"})
    except Exception as e:
        print(f"❌ SIGNUP ERROR: {str(e)}") 
        return Response({"status": "error", "message": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_profile(request):
    phone = request.GET.get('phone')
    if not phone:
        return JsonResponse({"status": "error", "message": "Phone parameter missing"}, status=400)

    try:
        user = User.objects.get(phone_number=phone)
        return JsonResponse({
            "status": "success",
            "name": user.first_name,
            "email": user.email,
            "phone": user.phone_number,
            "role": user.role,
            "vehicle_number": user.vehicle_number if hasattr(user, 'vehicle_number') else ""
        })
    except User.DoesNotExist:
        return JsonResponse({"status": "error", "message": "User not found"}, status=404)

# ==========================================
# 3. TRIP MANAGEMENT & LOGIC
# ==========================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_on_the_way(trip_source, trip_dest, customer_pickup, customer_drop):
    if trip_source['lat'] == 0.0 or trip_dest['lat'] == 0.0:
        return True
    total_route = haversine(trip_source['lat'], trip_source['lng'], trip_dest['lat'], trip_dest['lng'])
    leg1 = haversine(trip_source['lat'], trip_source['lng'], customer_pickup['lat'], customer_pickup['lng'])
    leg2 = haversine(customer_pickup['lat'], customer_pickup['lng'], trip_dest['lat'], trip_dest['lng'])
    if total_route == 0: return True 
    detour_percentage = ((leg1 + leg2) - total_route) / total_route
    return detour_percentage < 0.1

@csrf_exempt
def create_trip(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            driver_user = User.objects.get(phone_number=data['driver_phone'])
            
            # 🚀 CHECK VERIFICATION STATUS
            if not driver_user.is_verified:
                 return JsonResponse({
                     'error': 'Account Under Review. Please wait for Admin approval.'
                 }, status=403)

            new_trip = Trip.objects.create(
                driver=driver_user, 
                source_city=data['source_city'],
                destination_city=data['destination_city'],
                source_lat=data.get('source_lat', 0.0),
                source_lng=data.get('source_lng', 0.0),
                dest_lat=data.get('dest_lat', 0.0),
                dest_lng=data.get('dest_lng', 0.0),
                start_time=timezone.now(),
                price_per_seat=data['price'],
                available_seats=data['seats'],
                status='SCHEDULED'
            )
            return JsonResponse({'status': 'success', 'message': 'Trip Created!', 'trip_id': new_trip.id})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Driver not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def delete_trip(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            trip = Trip.objects.get(id=data['trip_id'])
            
            # Security: Ensure only the creator can delete
            # 🚀 FIX: Enhanced normalization to ensure matching works perfectly
            db_phone = str(trip.driver.phone_number).replace(" ", "").replace("+91", "").replace("-", "").strip()
            req_phone = str(data['driver_phone']).replace(" ", "").replace("+91", "").replace("-", "").strip()

            if db_phone == req_phone:
                trip.delete()
                return JsonResponse({'status': 'success', 'message': 'Route Deleted'})
            else:
                return JsonResponse({'error': 'Unauthorized: Phone mismatch'}, status=403)
        except Trip.DoesNotExist:
            return JsonResponse({'error': 'Trip not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

def get_driver_trips(request):
    phone = request.GET.get('phone')
    try:
        driver = User.objects.get(phone_number=phone)
        time_threshold = timezone.now() - timedelta(hours=24)
        
        # 🚀 AUTO DELETE LOGIC: This filter naturally hides trips older than 24h
        trips = Trip.objects.filter(driver=driver, status='SCHEDULED', start_time__gte=time_threshold)
        
        results = []
        for t in trips:
            results.append({
                'id': t.id,
                'source': t.source_city,
                'destination': t.destination_city,
                'seats': t.available_seats,
                'price': float(t.price_per_seat) 
            })
        return JsonResponse({'status': 'success', 'trips': results})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'})

def search_trips(request):
    s_city = request.GET.get('source_city')
    d_city = request.GET.get('destination_city')
    pickup_lat = float(request.GET.get('lat', 0.0))
    pickup_lng = float(request.GET.get('lng', 0.0))

    time_threshold = timezone.now() - timedelta(hours=24)
    # 🚀 AUTO DELETE LOGIC: We only search for trips created in the last 24h
    trips = Trip.objects.filter(
        status='SCHEDULED',
        available_seats__gt=0, 
        start_time__gte=time_threshold
    )

    if s_city: trips = trips.filter(source_city__iexact=s_city)
    if d_city: trips = trips.filter(destination_city__iexact=d_city)

    results = []
    for trip in trips:
        driver_source = {'lat': trip.source_lat, 'lng': trip.source_lng}
        driver_dest = {'lat': trip.dest_lat, 'lng': trip.dest_lng}
        customer_loc = {'lat': pickup_lat, 'lng': pickup_lng}
        
        if is_on_the_way(driver_source, driver_dest, customer_loc, driver_dest):
            results.append({
                'driver_name': trip.driver.first_name,
                # 🚀 CRITICAL FIX: Send Phone Number so Frontend 'Contact' button works!
                'driver_phone': trip.driver.phone_number, 
                'vehicle': trip.driver.vehicle_number if hasattr(trip.driver, 'vehicle_number') else trip.driver.license_number, 
                'price': float(trip.price_per_seat),
                'source': trip.source_city,
                'destination': trip.destination_city,
                'trip_id': trip.id,
                'seats_left': trip.available_seats 
            })
    return JsonResponse({'status': 'success', 'trips': results, 'count': len(results)})

# ==========================================
# 4. BOOKING APIs
# ==========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def book_seat(request):
    data = request.data
    try:
        trip = Trip.objects.get(id=data['trip_id'])
        user_id = data.get('user_id')
        user_phone = data.get('phone')
        
        if user_id:
            customer = User.objects.get(id=user_id)
        else:
            customer = User.objects.get(phone_number=user_phone)
            
        seats_wanted = int(data.get('seats', 1))
        
        if trip.available_seats < seats_wanted:
             return Response({'status': 'error', 'message': 'Not enough seats'}, status=400)

        cost = float(trip.price_per_seat) * seats_wanted
        
        booking = Booking.objects.create(
            trip=trip,
            customer=customer,
            seats_booked=seats_wanted,
            total_cost=cost,
            status='CONFIRMED'
        )
        
        # 🚀 LOGIC CHANGE: ZERO DECREMENT
        # We record the booking so the driver sees the name, 
        # BUT we do NOT subtract the seat count.
        # trip.available_seats -= seats_wanted 
        # trip.save()
        
        return Response({
            'status': 'success',
            'message': 'Booking Confirmed!', 
            'ticket_id': booking.id,
            'remaining_seats': trip.available_seats,
            'driver_details': {
                'name': trip.driver.first_name,
                'phone': trip.driver.phone_number,
                'vehicle': trip.driver.vehicle_number if hasattr(trip.driver, 'vehicle_number') else ""
            }
        })
    except (Trip.DoesNotExist, User.DoesNotExist):
        return Response({'status': 'error', 'message': 'Trip or Customer not found'}, status=404)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_bookings(request):
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
                'total_cost': float(b.total_cost),
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
                'revenue': float(b.total_cost),
                'status': b.status
            })
        return JsonResponse({'bookings': data})
    except Trip.DoesNotExist:
        return JsonResponse({'bookings': []})

@api_view(['GET'])
@permission_classes([AllowAny])
def get_trip_passengers(request):
    trip_id = request.GET.get('trip_id')
    phone = request.GET.get('phone')
    try:
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
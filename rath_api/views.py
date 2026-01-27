from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.html import strip_tags
from datetime import timedelta
from .models import Trip, User, Booking, EmailOTP 
from django.core.mail import send_mail            
from django.conf import settings
import json
import math
import random 

# --- IMPORTS FOR API ---
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# ==========================================
# 1. AUTHENTICATION & SECURITY (OTP SYSTEM)
# ==========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp_email(request):
    """
    Generates and Saves OTP.
    FIX APPLIED: Used 'update_or_create' to ensure OTP is definitely saved in DB.
    """
    email = request.data.get('email')
    role = request.data.get('role')

    if not email:
        return Response({"error": "Email address required"}, status=400)

    # 1. Generate 4-digit Code
    otp = str(random.randint(1000, 9999))
    
    # 2. FORCE SAVE to Database (Fixes the "Ghost OTP" bug)
    obj, created = EmailOTP.objects.update_or_create(
        email=email,
        defaults={'otp_code': otp}
    )
    
    print(f"💾 OTP SAVED TO DB: {obj.email} -> {obj.otp_code}") # Debug Log

    # 3. Determine Greeting
    if role == 'driver':
        subject = "Let's get moving! 🚗"
        greeting = "Hi Partner,"
        body_text = f"Ready to earn? Your login OTP is: {otp}"
        closing_text = "Have a productive day on the road!"
    else:
        subject = "Ready for your next trip? 🌍"
        greeting = "Hi there,"
        body_text = f"Your ride awaits! Your login OTP is: {otp}"
        closing_text = "Where are we going today?"

    # 4. Construct Email
    logo_voy = "https://atiuttam.com/assets/voy1.png"
    logo_atiu = "https://atiuttam.com/assets/atiubes.png"

    html_message = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2 style="color: #4A90E2;">{subject}</h2>
        <p><strong>{greeting}</strong></p>
        <p style="font-size: 16px;">{body_text}</p>
        <div style="background-color: #f4f4f4; padding: 15px; text-align: center; border-radius: 8px; margin: 20px 0;">
            <span style="font-size: 24px; letter-spacing: 5px; font-weight: bold; color: #000;">{otp}</span>
        </div>
        <p>{closing_text}</p>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 14px; color: #555;">
            Best Wishes,<br><strong>Voy by Atiuttam.com</strong>
        </p>
        <div style="margin-top: 15px;">
            <img src="{logo_voy}" alt="Voy Logo" height="50" style="margin-right: 15px; vertical-align: middle;">
            <img src="{logo_atiu}" alt="Atiuttam Logo" height="50" style="vertical-align: middle;">
        </div>
    </div>
    """
    plain_message = strip_tags(html_message)

    try:
        print(f"📧 SENDING EMAIL TO: {email} | OTP: {otp} | Role: {role}")
        send_mail(
            subject, plain_message, settings.EMAIL_HOST_USER, [email], 
            fail_silently=True, html_message=html_message
        )
        return Response({"status": "success", "message": "OTP Sent to Email"})
    except Exception as e:
        print(f"❌ EMAIL ERROR: {str(e)}")
        return Response({"error": "Failed to send email."}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_email(request):
    """
    Verifies OTP and returns User Status.
    FIX APPLIED: Returns 'is_verified' so App knows if it should block the driver.
    """
    email = request.data.get('email')
    otp = request.data.get('otp')

    try:
        otp_record = EmailOTP.objects.get(email=email)
        if otp_record.otp_code == otp:
            otp_record.delete() # OTP is single-use
            try:
                user = User.objects.get(email=email)
                return Response({
                    "status": "success",
                    "exists": True,
                    "role": user.role,
                    "name": user.first_name,
                    "user_id": user.id,
                    "is_verified": user.is_verified # 🚀 CRITICAL FOR APP LOGIC
                })
            except User.DoesNotExist:
                return Response({"status": "success", "exists": False})
        else:
            return Response({"error": "Invalid OTP Code"}, status=400)
    except EmailOTP.DoesNotExist:
        return Response({"error": "Please request a new Code"}, status=400)

# ==========================================
# 2. USER MANAGEMENT (SMART SIGNUP)
# ==========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def check_email(request):
    email = request.data.get('email')
    try:
        user = User.objects.get(email=email)
        return Response({
            "exists": True, "role": user.role, 
            "name": user.first_name, "user_id": user.id, 
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
        if not data.get('email') or not data.get('name'):
             return Response({"status": "error", "message": "Email/Name required"}, status=400)

        email = data['email']
        name = data['name']
        phone = data.get('phone', '')

        user, created = User.objects.get_or_create(
            email=email, defaults={'username': email} 
        )
        
        user.first_name = name
        if phone: user.phone_number = phone
        user.role = 'customer'
        user.is_verified = True 
        user.save()
        
        return Response({"status": "success", "user_id": user.id, "role": "customer"})
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser]) 
def signup_driver(request):
    try:
        print("\n🚀 DEBUG START: Driver Signup 🚀")
        
        # 1. CHECK FOR FILES
        # If this list is empty, the App (Frontend) is sending an empty envelope
        print(f"📁 FILES RECEIVED: {request.FILES.keys()}")
        
        if not request.FILES:
            print("❌ ERROR: Request has NO files. The App is not sending them correctly.")
            return Response({"status": "error", "message": "Server received 0 files. Check App FormData."}, status=400)

        # 2. Grab Data
        data = request.data
        email = data.get('email')
        
        user, created = User.objects.get_or_create(email=email, defaults={'username': email})
        
        # 3. FORCE SAVE IMAGES
        # We explicitly print what we are saving
        if 'profile_photo' in request.FILES: 
            print("   -> Saving Profile Photo...")
            user.profile_photo = request.FILES['profile_photo']
            
        if 'license_photo' in request.FILES: 
            print("   -> Saving License Photo...")
            user.license_photo = request.FILES['license_photo']
            
        if 'rc_photo' in request.FILES: 
            user.rc_photo = request.FILES['rc_photo']
            
        if 'aadhaar_photo' in request.FILES: 
            user.aadhaar_photo = request.FILES['aadhaar_photo']

        # 4. Save Details
        user.role = 'driver'
        user.is_verified = False
        user.first_name = data.get('fullName', user.first_name)
        user.phone_number = data.get('phone', user.phone_number)
        user.vehicle_number = data.get('vehicle_number', user.vehicle_number)
        
        user.save()
        print(f"✅ SUCCESS: Saved User {user.email}")
        
        return Response({"status": "success", "user_id": user.id})

    except Exception as e:
        print(f"❌ CRASH: {str(e)}") 
        return Response({"status": "error", "message": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_profile(request):
    email = request.GET.get('email')
    if not email: return JsonResponse({"status": "error"}, status=400)
    try:
        user = User.objects.get(email=email)
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
            driver_user = User.objects.get(email=data['driver_email'])
            
            if not driver_user.is_verified:
                 return JsonResponse({'error': 'Account Under Review.'}, status=403)

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
            if trip.driver.email == data['driver_email']:
                trip.delete()
                return JsonResponse({'status': 'success', 'message': 'Route Deleted'})
            else:
                return JsonResponse({'error': 'Unauthorized'}, status=403)
        except Trip.DoesNotExist:
            return JsonResponse({'error': 'Trip not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

def get_driver_trips(request):
    email = request.GET.get('email')
    try:
        driver = User.objects.get(email=email)
        time_threshold = timezone.now() - timedelta(hours=24)
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
                'driver_phone': trip.driver.phone_number if trip.driver.phone_number else "Contact via App", 
                'vehicle': trip.driver.vehicle_number if hasattr(trip.driver, 'vehicle_number') else "", 
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
        email = data.get('email')
        
        if user_id:
            customer = User.objects.get(id=user_id)
        else:
            customer = User.objects.get(email=email)
            
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
    email = request.GET.get('email')
    try:
        customer = User.objects.get(email=email)
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
    email = request.GET.get('email')
    try:
        trip = Trip.objects.get(id=trip_id, driver__email=email)
        bookings = Booking.objects.filter(trip=trip)
        passengers = []
        for b in bookings:
            passengers.append({
                "name": b.customer.first_name,
                "phone": b.customer.phone_number if b.customer.phone_number else "Email User",
                "seats": b.seats_booked,
                "status": b.status
            })
        return JsonResponse({"status": "success", "passengers": passengers})
    except Trip.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Trip not found or unauthorized"}, status=404)
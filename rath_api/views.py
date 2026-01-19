from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Trip, User, Booking
import json
import math

# --- NEW IMPORTS FOR API (The Bridge) ---
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# ==========================================
# 1. AUTHENTICATION & USER MANAGEMENT (NEW)
# ==========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def check_phone(request):
    """Checks if phone exists to decide between Login or Signup"""
    phone = request.data.get('phone')
    try:
        # FIX 1: Changed 'phone=' to 'phone_number='
        user = User.objects.get(phone_number=phone)
        return Response({
            "exists": True, 
            "role": user.user_type, 
            "name": user.name,
            "user_id": user.id
        })
    except User.DoesNotExist:
        return Response({"exists": False})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def signup_customer(request):
    """Registers a new Passenger"""
    data = request.data
    try:
        user = User.objects.create(
            # FIX 2: Changed 'phone=' to 'phone_number='
            phone_number=data['phone'],
            name=data['name'],
            email=data.get('email', ''),
            user_type='customer'
        )
        return Response({"status": "success", "user_id": user.id, "role": "customer"})
    except Exception as e:
        return Response({"status": "error", "message": str(e)})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def signup_driver(request):
    """Registers a new Driver"""
    data = request.data
    try:
        user = User.objects.create(
            # FIX 3: Changed 'phone=' to 'phone_number='
            phone_number=data['phone'],
            name=data['fullName'],
            user_type='driver',
            license_number=data.get('vehicleNumber', ''),
            is_verified=False  # Pending Approval
        )
        return Response({"status": "success", "user_id": user.id, "role": "driver"})
    except Exception as e:
        return Response({"status": "error", "message": str(e)})


# ==========================================
# 2. THE MATH SECTION (Rubber Band Logic)
# ==========================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_on_the_way(trip_source, trip_dest, customer_pickup, customer_drop):
    total_route = haversine(trip_source['lat'], trip_source['lng'], trip_dest['lat'], trip_dest['lng'])
    leg1 = haversine(trip_source['lat'], trip_source['lng'], customer_pickup['lat'], customer_pickup['lng'])
    leg2 = haversine(customer_pickup['lat'], customer_pickup['lng'], trip_dest['lat'], trip_dest['lng'])
    
    # Allow 10% detour
    detour_percentage = ((leg1 + leg2) - total_route) / total_route
    return detour_percentage < 0.1

# ==========================================
# 3. TRIP MANAGEMENT APIs
# ==========================================

@csrf_exempt
def create_trip(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            # FIX 4: Changed 'phone=' to 'phone_number='
            driver_user = User.objects.get(phone_number=data['driver_phone'])
            # Check if driver is verified before letting them post
            if not driver_user.is_verified:
                 return JsonResponse({'error': 'Driver not verified yet'}, status=403)
                 
        except User.DoesNotExist:
            return JsonResponse({'error': 'Driver not found'}, status=404)

        new_trip = Trip.objects.create(
            driver=driver_user, # Linked to the User directly
            source_city=data['source_city'],
            destination_city=data['destination_city'],
            source_lat=data['source_lat'],
            source_lng=data['source_lng'],
            dest_lat=data['dest_lat'],
            dest_lng=data['dest_lng'],
            start_time=timezone.now(),
            price_per_seat=data['price'],
            available_seats=data['seats'],
            status='SCHEDULED'
        )
        return JsonResponse({'message': 'Trip Created!', 'trip_id': new_trip.id})

def search_trips(request):
    try:
        pickup_lat = float(request.GET.get('lat'))
        pickup_lng = float(request.GET.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Please provide lat and lng'}, status=400)

    all_trips = Trip.objects.filter(status='SCHEDULED')
    results = []

    for trip in all_trips:
        driver_source = {'lat': trip.source_lat, 'lng': trip.source_lng}
        driver_dest = {'lat': trip.dest_lat, 'lng': trip.dest_lng}
        customer_loc = {'lat': pickup_lat, 'lng': pickup_lng}
        
        # Check if the driver is passing by
        if is_on_the_way(driver_source, driver_dest, customer_loc, driver_dest):
            results.append({
                'driver_name': trip.driver.name,
                'vehicle': trip.driver.license_number, # Using license/vehicle field
                'price': trip.price_per_seat,
                'source': trip.source_city,
                'destination': trip.destination_city,
                'trip_id': trip.id 
            })
            
    return JsonResponse({'results': results, 'count': len(results)})

# ==========================================
# 4. BOOKING APIs
# ==========================================

@csrf_exempt
def book_seat(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        
        try:
            trip = Trip.objects.get(id=data['trip_id'])
            # Find customer by ID or Phone
            customer = User.objects.get(id=data.get('user_id')) 
        except (Trip.DoesNotExist, User.DoesNotExist):
            return JsonResponse({'error': 'Trip or Customer not found'}, status=404)
            
        seats_wanted = int(data.get('seats', 1))
        
        if trip.available_seats < seats_wanted:
            return JsonResponse({'error': 'Not enough seats!'}, status=400)
            
        cost = float(trip.price_per_seat) * seats_wanted
        
        booking = Booking.objects.create(
            trip=trip,
            customer=customer,
            seats_booked=seats_wanted,
            total_cost=cost,
            status='CONFIRMED'
        )
        
        trip.available_seats -= seats_wanted
        trip.save()
        
        return JsonResponse({
            'message': 'Booking Confirmed!', 
            'ticket_id': booking.id,
            'remaining_seats': trip.available_seats
        })

def get_trip_bookings(request):
    trip_id = request.GET.get('trip_id')
    try:
        trip = Trip.objects.get(id=trip_id)
        bookings = trip.bookings.all()
        
        data = []
        for b in bookings:
            data.append({
                'customer': b.customer.name,
                'seats': b.seats_booked,
                'revenue': b.total_cost,
                'status': b.status
            })
        return JsonResponse({'bookings': data})
    except Trip.DoesNotExist:
        return JsonResponse({'bookings': []})
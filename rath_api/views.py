from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Trip, User, Booking
import json
import math

# --- IMPORTS FOR API ---
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# ==========================================
# 1. AUTHENTICATION & USER MANAGEMENT (SECURE)
# ==========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def check_phone(request):
    """
    SECURITY CHECK:
    - Checks if user exists.
    - Returns 'is_verified' status so App knows to block unapproved drivers.
    """
    phone = request.data.get('phone')
    try:
        user = User.objects.get(phone_number=phone)
        return Response({
            "exists": True, 
            "role": user.role, 
            "name": user.first_name,
            "user_id": user.id,
            # SECURITY: This tells the app if the Admin has approved them
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
        user = User.objects.create(
            phone_number=data['phone'],
            first_name=data['name'],
            email=data.get('email', ''),
            role='customer',
            is_verified=True # Customers don't need manual approval
        )
        return Response({"status": "success", "user_id": user.id, "role": "customer"})
    except Exception as e:
        return Response({"status": "error", "message": str(e)})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def signup_driver(request):
    """Registers a new Driver (REQUIRES APPROVAL)"""
    data = request.data
    try:
        user = User.objects.create(
            phone_number=data['phone'],
            first_name=data['fullName'],
            role='driver',
            license_number=data.get('vehicleNumber', ''),
            is_verified=False # SECURITY: Drivers must wait for Admin Approval
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
    """
    SECURITY ENFORCEMENT:
    - Only allows VERIFIED drivers to post trips.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            driver_user = User.objects.get(phone_number=data['driver_phone'])
            
            # SECURITY BLOCK: If Admin hasn't approved, reject request.
            if not driver_user.is_verified:
                 return JsonResponse({
                     'error': 'Account Under Review. Please wait for Admin approval.'
                 }, status=403)
                 
        except User.DoesNotExist:
            return JsonResponse({'error': 'Driver not found'}, status=404)

        new_trip = Trip.objects.create(
            driver=driver_user, 
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
        
        if is_on_the_way(driver_source, driver_dest, customer_loc, driver_dest):
            results.append({
                'driver_name': trip.driver.first_name,
                'vehicle': trip.driver.license_number, 
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
                'customer': b.customer.first_name,
                'seats': b.seats_booked,
                'revenue': b.total_cost,
                'status': b.status
            })
        return JsonResponse({'bookings': data})
    except Trip.DoesNotExist:
        return JsonResponse({'bookings': []})
from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('send-otp/', views.send_otp),
    path('verify-otp/', views.verify_otp),
    path('signup-customer/', views.signup_customer),
    path('signup-driver/', views.signup_driver),
    
    # 🚀 NEW: Profile Management (Fixes missing name/email)
    path('get-profile/', views.get_profile),

    # Trip Management
    path('create-trip/', views.create_trip),
    path('search-trips/', views.search_trips),
    
    # Driver Dashboard Endpoints
    path('get-driver-trips/', views.get_driver_trips), 
    path('delete-trip/', views.delete_trip),
    path('get-passengers/', views.get_trip_passengers), 
    
    # Passenger Ticket Endpoint
    path('get-user-bookings/', views.get_user_bookings), 
    
    # Booking
    path('book-seat/', views.book_seat),
]
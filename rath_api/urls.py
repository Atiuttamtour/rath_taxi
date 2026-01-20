from django.urls import path
from . import views

urlpatterns = [
    # --- Authentication ---
    path('send-otp/', views.send_otp),
    path('verify-otp/', views.verify_otp),
    path('signup-customer/', views.signup_customer),
    path('signup-driver/', views.signup_driver),
    path('get-profile/', views.get_profile),

    # --- Trip Management ---
    path('create-trip/', views.create_trip),
    path('search-trips/', views.search_trips),
    path('book-seat/', views.book_seat),
    
    # --- Driver Dashboard ---
    path('get-driver-trips/', views.get_driver_trips), 
    path('delete-trip/', views.delete_trip),
    path('get-passengers/', views.get_trip_passengers), 
    
    # --- User Bookings ---
    path('get-user-bookings/', views.get_user_bookings), 
]
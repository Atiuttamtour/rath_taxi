from django.contrib import admin
from django.urls import path
from rath_api import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin Panel
    path('admin/', admin.site.urls),

    # --- AUTH & USER APIs ---
    # 🚀 FIX: Removed 'api/' from start because the Project URL already handles it
    path('send-otp/', views.send_otp),
    path('verify-otp/', views.verify_otp),
    path('check-phone/', views.check_phone),
    path('signup-customer/', views.signup_customer),
    path('signup-driver/', views.signup_driver), # The one we are testing!
    path('get-profile/', views.get_profile),

    # --- TRIP & BOOKING APIs ---
    path('create-trip/', views.create_trip),
    path('delete-trip/', views.delete_trip),
    path('get-driver-trips/', views.get_driver_trips),
    path('search-trips/', views.search_trips),
    path('book-seat/', views.book_seat),
    path('get-user-bookings/', views.get_user_bookings),
    path('get-trip-bookings/', views.get_trip_bookings),
    path('get-trip-passengers/', views.get_trip_passengers),
]

# 🚀 SERVE IMAGES IN ADMIN PANEL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.urls import path
from . import views

urlpatterns = [
    path('check-phone/', views.check_phone),
    path('signup-customer/', views.signup_customer),
    path('signup-driver/', views.signup_driver),
]
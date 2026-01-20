# backend/atiuttam_project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('rath_api.urls')),  # <--- THIS LINE IS CRITICAL
]
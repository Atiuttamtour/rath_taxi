from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('rath_api.urls')),  # <--- Connects to your App
]

# PROFESSIONAL ADDITION:
# This tells the server: "If the app asks for an image, get it from the media folder."
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
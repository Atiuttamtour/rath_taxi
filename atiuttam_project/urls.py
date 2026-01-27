from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse # Import this to show a simple message

# A simple function to show the server is alive
def home_view(request):
    return HttpResponse("<h1>Voy API is Running</h1><p>Driver and Passenger services are active.</p>")

urlpatterns = [
    path('', home_view), # <--- This fixes the 404 at the root URL
    path('admin/', admin.site.urls),
    path('api/', include('rath_api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
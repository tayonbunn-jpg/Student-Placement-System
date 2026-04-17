"""
URL configuration for placement_system project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.authentication.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('upload/', include('apps.data_uploads.urls')),  # Changed from data_upload to data_uploads
    path('ml/', include('apps.ml_engine.urls')),
    path('reports/', include('apps.reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
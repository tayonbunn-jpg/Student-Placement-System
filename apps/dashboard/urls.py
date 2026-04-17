from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/stats/', views.get_dashboard_stats, name='dashboard_stats'),
]
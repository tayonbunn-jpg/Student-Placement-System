from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/stats/', views.get_dashboard_stats, name='dashboard_stats'),
    path('delete-prediction/<int:record_id>/', views.delete_prediction, name='delete_prediction'),
    path('about/', views.about, name='about'),  
]
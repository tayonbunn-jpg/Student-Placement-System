from django.urls import path
from . import views

urlpatterns = [
    path('', views.generate_report, name='generate_report'),
    path('download/', views.download_report, name='download_report'),
]
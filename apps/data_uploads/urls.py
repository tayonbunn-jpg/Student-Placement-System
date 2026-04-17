from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_data, name='upload_data'),
    path('preprocess/', views.preprocess_data, name='preprocess_data'),
]
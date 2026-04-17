from django.urls import path
from . import views

urlpatterns = [
    path('train/', views.train_model, name='train_model'),
    path('predict/', views.make_prediction, name='predict'),
    path('models/', views.list_models, name='list_models'),
    path('predictions/', views.prediction_history, name='prediction_history'),
]
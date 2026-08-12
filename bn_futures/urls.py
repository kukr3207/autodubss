from django.urls import path
from bn_futures import views

urlpatterns = [
    path('execute/', views.execute_bn_futures_bot, name='execute_bn_futures_bot'),
]

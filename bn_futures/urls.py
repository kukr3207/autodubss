from django.urls import path
from bn_futures import views

urlpatterns = [
    path('', views.executeBNFuturesBot, name='executeBNFuturesBot'),
]

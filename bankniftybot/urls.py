from django.urls import path
from bankniftybot import views

urlpatterns = [
    path('', views.bankNiftyBot, name='bankniftybot'),
    path('report',views.generateReport, name="generateReport")
]


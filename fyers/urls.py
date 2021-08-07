from django.urls import path
from fyers import views

urlpatterns = [
    path('', views.bankNiftyBotFyers, name='fyers'),
    path('report',views.generateReport, name="generateReport")
]


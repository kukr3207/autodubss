from django.urls import path
from fyers import views

urlpatterns = [
    path('', views.fyersAuthentication, name='fyers'),
    path('banknifty',views.bankniftybot,name='bankniftybot_fyers'),
    path('crudeoil',views.crudeoilbot,name='crudeoilbot_fyers'),
    path('report',views.generateReport, name="generateReport"),
    path('fyersauthentication',views.fyers,name='fyers_page')
]

from django.urls import path
from home import views as home_view

urlpatterns = [
    path('', home_view.fyersAuthentication, name='fyersAuthentication'),
    path('fyersAuthenticationCallback',home_view.fyersAuthenticationCallback,name='fyersAuthenticationCallback'),
    path('bnfuturesbot',home_view.bnFuturesForm,name='bn_futures_bot_url'),
    path('bnoptionsbot',home_view.bnOptionsForm,name='bn_options_bot_url'),
]

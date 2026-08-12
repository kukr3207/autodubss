from django.urls import path
from home import views as home_view

urlpatterns = [
    path('', home_view.home, name='home'),
    path('fyers/authenticate/', home_view.fyers_authentication, name='fyers_authentication'),
    path('fyers/callback/', home_view.fyers_authentication_callback, name='fyers_authentication_callback'),
    path('bots/futures/', home_view.bn_futures_form, name='bn_futures_bot_url'),
    path('bots/options/', home_view.bn_options_form, name='bn_options_bot_url'),
]

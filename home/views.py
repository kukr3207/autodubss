from django.shortcuts import render
from django.shortcuts import redirect
from home.models import User, UserFyersAppRelation
from .forms import UserBNFuturesRelationForm, UserBNOptionsRelationForm
from django.contrib.auth.decorators import login_required
from fyers_api import accessToken
from django.contrib import messages  
from django.utils.safestring import mark_safe  

REDIRECT_URL = "https://algo-trading-01.herokuapp.com/fyersAuthenticationCallback"

# Create your views here.
@login_required
def home(request):	
    bn_futures_form = UserBNFuturesRelationForm(request.POST or None)
    context = {
        'bn_futures_form':bn_futures_form,
    }	
    return render(request, "home.html", context)

@login_required
def fyersAuthentication(request):
    user_id = User.objects.get(pk=request.user.id).__dict__['id']
    user_fyers_app = UserFyersAppRelation.objects.get(user_id=user_id).__dict__
    app_id = user_fyers_app['fyers_app_id']
    app_secret = user_fyers_app['fyers_app_secretkey']
    redirect_uri = REDIRECT_URL
    session=accessToken.SessionModel(client_id=app_id,
            secret_key=app_secret,
            redirect_uri=redirect_uri, 
            response_type="code", 
            grant_type="authorization_code",)
    response = session.generate_authcode()  
    return redirect(response)

@login_required
def fyersAuthenticationCallback(request):
    auth_code = request.GET.get('auth_code')
    user_id = User.objects.get(pk=request.user.id).__dict__['id']
    user_fyers_app = UserFyersAppRelation.objects.get(user_id=user_id).__dict__
    app_id = user_fyers_app['fyers_app_id']
    app_secret = user_fyers_app['fyers_app_secretkey']
    redirect_uri = REDIRECT_URL
    session=accessToken.SessionModel(client_id=app_id,
            secret_key=app_secret,
            redirect_uri=redirect_uri, 
            response_type="code", 
            grant_type="authorization_code",)
    session.set_token(auth_code)
    response = session.generate_token()
    print(response)
    access_token = response["access_token"]
    request.session['fyers_access_token'] = access_token
    bn_futures_form = UserBNFuturesRelationForm(request.POST or None)
    bn_options_form = UserBNOptionsRelationForm(request.POST or None)
    context = {
        'bn_futures_form': bn_futures_form,
        'bn_options_form': bn_options_form,
    }
    return render(request, "home.html", context)

def bnFuturesForm(request):
    bn_futures_form = UserBNFuturesRelationForm(request.POST or None)
    if request.method == "POST":
        if request.user.is_authenticated:
            if bn_futures_form.is_valid():
                bn_futures_form_obj = bn_futures_form.save(commit=False)
                bn_futures_form_obj.user_id = User.objects.get(pk=request.user.id)
                if request.session['fyers_access_token']:
                    bn_futures_form_obj.fyers_access_token = request.session['fyers_access_token']
                bn_futures_form_obj.save()
                messages.success(request, mark_safe('Bank-Nifty order submitted successfully. <br/> Check your account at 9:20AM'))
    bn_futures_form = UserBNFuturesRelationForm(request.POST or None)
    bn_options_form = UserBNOptionsRelationForm(request.POST or None)
    context = {
        'bn_futures_form': bn_futures_form,
        'bn_options_form': bn_options_form,
    }
    return render(request, 'home.html', context)

def bnOptionsForm(request):
    bn_options_form = UserBNOptionsRelationForm(request.POST or None)
    if request.method == "POST":
        if request.user.is_authenticated:
            if bn_options_form.is_valid():
                bn_options_form_obj = bn_options_form.save(commit=False)
                bn_options_form_obj.user_id = User.objects.get(pk=request.user.id)
                if request.session['fyers_access_token']:
                    bn_options_form_obj.fyers_access_token = request.session['fyers_access_token']
                bn_options_form_obj.save()
                messages.success(request, mark_safe('Bank-Nifty order submitted successfully. <br/> Check your account at 9:20AM'))
    bn_options_form = UserBNOptionsRelationForm(request.POST or None)
    bn_futures_form = UserBNFuturesRelationForm(request.POST or None)
    context = {
        'bn_futures_form':bn_futures_form,
        'bn_options_form': bn_options_form,
    }
    return render(request, 'home.html', context)


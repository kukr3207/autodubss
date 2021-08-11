from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import User
from .forms import UserBankniftyFyersRelationForm, UserCrudeoilFyersRelationForm
from .models import UserBankniftyFyersRelation, UserCrudeoilFyersRelation, UserFyersAppRelation
from .main import StockMarket
from .fyers_authentication import fyersOAuth
from .cron import Command
import json
# Create your views here.

@login_required
def fyersAuthentication(request):
	user_id = User.objects.get(pk=request.user.id).__dict__['id']
	try:
		user_fyers_app = UserFyersAppRelation.objects.get(user_id=user_id).__dict__
		app_id = user_fyers_app['fyers_app_id']
		app_secret = user_fyers_app['fyers_app_secretkey']
		html = fyersOAuth(app_id, app_secret)
	except Exception as e:
		print(e)
		print("Fyers app does not exist. Please contact admin.")
		html = "Fyers app does not exist. Please contact admin."
	return HttpResponse(html)

@login_required
def fyers(request):
	access_token = request.GET.get('access_token')
	request.session['fyers_access_token'] = access_token
	banknifty_form = UserBankniftyFyersRelationForm(request.POST or None)
	crudeoil_form = UserCrudeoilFyersRelationForm(request.POST or None)
	context = {
		'banknifty_form':banknifty_form,
		'crudeoil_form':crudeoil_form,
	}
	return render(request, "fyers_homepage.html", context)

@login_required
def bankniftybot(request):
	banknifty_form = UserBankniftyFyersRelationForm(request.POST or None)
	if request.method == "POST":
		if request.user.is_authenticated:
			if banknifty_form.is_valid():
				banknifty_form_obj = banknifty_form.save(commit=False) # Return an object without saving to the DB
				banknifty_form_obj.user_id = User.objects.get(pk=request.user.id) # Add an author field which will contain current user's id
				# print(form_obj.trading_platform)
				c = Command()  
				stock = "  "
				#algo_obj = StockMarket()
				#algo_obj.run(1)
				access_token = request.session['fyers_access_token']
				c.bankniftyScheduler(access_token,#banknifty_form_obj.fyers_id,banknifty_form_obj.fyers_password,banknifty_form_obj.fyers_pan_dob,
						banknifty_form_obj.number_of_lots,request.user,stock,banknifty_form_obj)
			else:
				print("ERROR : Form is invalid")
				print(form.errors)
	banknifty_form = UserBankniftyFyersRelationForm(request.POST or None)
	crudeoil_form = UserCrudeoilFyersRelationForm(request.POST or None)
	context = {
		'banknifty_form':banknifty_form,
		'crudeoil_form':crudeoil_form
	}			
	return render(request, 'fyers_homepage.html', context)


@login_required
def crudeoilbot(request):
	crudeoil_form = UserCrudeoilFyersRelationForm(request.POST or None)
	if request.method == "POST":
		if request.user.is_authenticated:
			if crudeoil_form.is_valid():
				crudeoil_form_obj = crudeoil_form.save(commit=False) # Return an object without saving to the DB
				crudeoil_form_obj.user_id = User.objects.get(pk=request.user.id) # Add an author field which will contain current user's id
				# print(form_obj.trading_platform)
				c = Command()  
				stock = "  "
				access_token = request.session['fyers_access_token']
				c.crudeoilScheduler(access_token,#banknifty_form_obj.fyers_id,banknifty_form_obj.fyers_password,banknifty_form_obj.fyers_pan_dob,
						crudeoil_form_obj.number_of_lots,request.user,stock,crudeoil_form_obj)
			else:
				print("ERROR : Form is invalid")
				print(form.errors)
	banknifty_form = UserBankniftyFyersRelationForm(request.POST or None)
	crudeoil_form = UserCrudeoilFyersRelationForm(request.POST or None)
	context = {
		'banknifty_form':banknifty_form,
		'crudeoil_form':crudeoil_form
	}			
	return render(request, 'fyers_homepage.html', context)

def generateReport(request):
	current_user = request.user
	current_user_id = current_user.id
	db_records = UserLotsInput.objects.filter(user_id=current_user_id)
	form = UserLotsInputForm(request.POST or None)
	l = []
	for i in db_records:
		temp_list = {}
		temp_list['date'] = i.date_added.strftime("%Y-%m-%d")
		temp_list['stock'] = (i.stock)
		temp_list['Number_of_Lots'] = (i.number_of_lots)
		temp_list['P&L'] = (i.p_and_l)
		l.append(temp_list)
	context = {
		'report': l,
		'form': form
	}
	return render(request, 'fyers_homepage.html', context)

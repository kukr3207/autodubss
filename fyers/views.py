from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import User
from .forms import UserBankniftyFyersRelationForm, UserCrudeoilFyersRelationForm
from .models import UserBankniftyFyersRelation, UserCrudeoilFyersRelation, UserFyersAppRelation, UserSubscriptionRelation
from .main import StockMarket
from .fyers_authentication import fyersOAuth
from .cron import Command
import json
import datetime
from algo_trading.settings import TIME_ZONE
from django.utils import timezone
from django.utils.timezone import activate
activate(TIME_ZONE)
from datetime import timedelta
import pytz
from django.views.decorators.csrf import csrf_exempt   
from .crudeoil import CrudeoilBot   
import time                 
from django.contrib import messages  
from django.utils.safestring import mark_safe                  
# Create your views here.


@login_required
@csrf_exempt
def fyersAuthentication(request):
	user_id = User.objects.get(pk=request.user.id).__dict__['id']
	try:
		user_fyers_app = UserFyersAppRelation.objects.get(user_id=user_id).__dict__
		app_id = user_fyers_app['fyers_app_id']
		app_secret = user_fyers_app['fyers_app_secretkey']
		html = fyersOAuth(app_id, app_secret)
	except Exception as e:
		try:
			user_fyers_app = UserFyersAppRelation.objects.get(user_id=user_id).__dict__
			app_id = user_fyers_app['fyers_app_id']
			app_secret = user_fyers_app['fyers_app_secretkey']
			html = fyersOAuth(app_id, app_secret)
			time.sleep(2)
		except:
			print(e)
			print("Fyers app does not exist. Please contact admin.")
			html = "Fyers app does not exist. Please contact admin."
	return HttpResponse(html)

@login_required
@csrf_exempt
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
@csrf_exempt
def bankniftybot(request):
	banknifty_form = UserBankniftyFyersRelationForm(request.POST or None)
	if request.method == "POST":
		if request.user.is_authenticated:
			if banknifty_form.is_valid():
				banknifty_form_obj = banknifty_form.save(commit=False) # Return an object without saving to the DB
				banknifty_form_obj.user_id = User.objects.get(pk=request.user.id) # Add an author field which will contain current user's id
				stock = "  "
				access_token = request.session['fyers_access_token']
				current_time = datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')).time()
				banknifty_execution_time = current_time.replace(hour=9,minute=18,second=0)
				market_closing_time = current_time.replace(hour=15,minute=30,second=0)
				print(current_time,banknifty_execution_time,market_closing_time)
				if (current_time < banknifty_execution_time) or (current_time > market_closing_time):
				# if True:
					c = Command()  
					c.bankniftyScheduler(access_token,#banknifty_form_obj.fyers_id,banknifty_form_obj.fyers_password,banknifty_form_obj.fyers_pan_dob,
							banknifty_form_obj.number_of_lots,request.user,stock,banknifty_form_obj)
					messages.success(request, mark_safe('Bank-Nifty order submitted successfully. <br/> Check your account at 9:20AM'))
				else:
					print(" Banknifty timing is not right ")
					messages.success(request, mark_safe('Bank-Nifty order submittion failed. <br/> Order should be placed between 7AM-9:18AM'))

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
@csrf_exempt
def crudeoilbot(request):
	crudeoil_form = UserCrudeoilFyersRelationForm(request.POST or None)
	if request.method == "POST":
		if request.user.is_authenticated:
			if crudeoil_form.is_valid():
				crudeoil_form_obj = crudeoil_form.save(commit=False) # Return an object without saving to the DB
				crudeoil_form_obj.user_id = User.objects.get(pk=request.user.id) # Add an author field which will contain current user's id
				# print(form_obj.trading_platform) 
				stock = "  "
				access_token = request.session['fyers_access_token']
				current_time = datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')).time()
				crudeoil_execution_time = current_time.replace(hour=9,minute=10,second=0)
				market_closing_time = current_time.replace(hour=22,minute=0,second=0)
				print(current_time,crudeoil_execution_time,market_closing_time)
				if (current_time < crudeoil_execution_time) or (current_time > market_closing_time):
					c = Command() 
					c.crudeoilScheduler(access_token,#banknifty_form_obj.fyers_id,banknifty_form_obj.fyers_password,banknifty_form_obj.fyers_pan_dob,
							crudeoil_form_obj.number_of_lots,request.user,stock,crudeoil_form_obj)
					messages.success(request, mark_safe('Crude-Oil order submitted successfully. <br/> Check your account at 9:20AM'))
				else:
					algo_obj = CrudeoilBot(access_token)
					order_id_1, order_id_2 = algo_obj.run(crudeoil_form_obj.number_of_lots,request.user)
					crudeoil_form_obj.stock = stock
					crudeoil_form_obj.order_id_1 = str(order_id_1)
					crudeoil_form_obj.order_id_2 = str(order_id_2)
					crudeoil_form_obj.save() # Save the final "real form" to the DB
					messages.success(request, mark_safe('Crude-Oil order submitted successfully. <br/> Order will be placed with few minutes'))
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
	isSubscribed(current_user_id)
	# db_records = UserLotsInput.objects.filter(user_id=current_user_id)
	# form = UserLotsInputForm(request.POST or None)
	# l = []
	# for i in db_records:
	# 	temp_list = {}
	# 	temp_list['date'] = i.date_added.strftime("%Y-%m-%d")
	# 	temp_list['stock'] = (i.stock)
	# 	temp_list['Number_of_Lots'] = (i.number_of_lots)
	# 	temp_list['P&L'] = (i.p_and_l)
	# 	l.append(temp_list)
	banknifty_form = UserBankniftyFyersRelationForm(request.POST or None)
	crudeoil_form = UserCrudeoilFyersRelationForm(request.POST or None)
	context = {
		'banknifty_form':banknifty_form,
		'crudeoil_form':crudeoil_form
	}			
	return render(request, 'fyers_homepage.html', context)


from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import User
from .forms import UserLotsInputForm
from .models import UserLotsInput
from .main import StockMarket
from .cron import Command
import json
# Create your views here.

@login_required
def bankNiftyBotFyers(request):
	form = UserLotsInputForm(request.POST or None)
	if request.method == "POST":
		if request.user.is_authenticated:
			if form.is_valid():
				form_obj = form.save(commit=False) # Return an object without saving to the DB
				form_obj.user_id = User.objects.get(pk=request.user.id) # Add an author field which will contain current user's id
				# print(form_obj.trading_platform)
				c = Command()  
				stock = "  "
				c.handle(form_obj.fyers_id,form_obj.fyers_password,form_obj.fyers_pan_dob,form_obj.number_of_lots,request.user,stock,form_obj)
			else:
				print("ERROR : Form is invalid")
				print(form.errors)

	context = {
		'form':form
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

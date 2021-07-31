from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import User
from .forms import UserLotsInputForm
from .models import UserLotsInput
from .main import StockMarket
import json
# Create your views here.

@login_required
def bankNiftyBot(request):
	form = UserLotsInputForm(request.POST or None)
	if request.method == "POST":
		if request.user.is_authenticated:
			# form['user_id'] = User.objects.get(pk=request.user.id)
			# form['number_of_lots'] = request.POST["number_of_lots"]
			if form.is_valid():
				form_obj = form.save(commit=False) # Return an object without saving to the DB
				form_obj.user_id = User.objects.get(pk=request.user.id) # Add an author field which will contain current user's id
				algo_obj = StockMarket(form_obj.fyers_id,form_obj.fyers_password,form_obj.fyers_pan_dob)
				order_id_1, order_id_2 = algo_obj.run(form_obj.number_of_lots,request.user)
				stock = "BANKNIFTY21JULFUT"
				stock = form_obj.stock
				form_obj.stock = stock
				form_obj.order_id_1 = str(order_id_1)
				form_obj.order_id_2 = str(order_id_2)
				form_obj.save() # Save the final "real form" to the DB
			else:
				print("ERROR : Form is invalid")
				print(form.errors)

	context = {
		'form':form
	}

	return render(request, 'bankniftybot_homepage.html', context)

def generateReport(request):
	current_user = request.user
	current_user_id = current_user.id
	db_records = UserLotsInput.objects.filter(user_id=current_user_id)
	l = []
	for i in db_records:
		temp_list = {}
		temp_list['date'] = i.date_added.strftime("%Y-%m-%d")
		temp_list['stock'] = (i.stock)
		temp_list['Number_of_Lots'] = (i.number_of_lots)
		temp_list['P&L'] = (i.p_and_l)
		l.append(temp_list)
	context = {
		'report': l
	}
	return render(request, 'bankniftybot_homepage.html', context)
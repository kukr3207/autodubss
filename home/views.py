from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from fyers.models import UserBankniftyFyersRelation, UserCrudeoilFyersRelation, UserFyersAppRelation, UserSubscriptionRelation
import datetime
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt

# Create your views here.
@login_required
@csrf_exempt
def home(request):
    current_user_id = request.user.id
    subscription_flag = isSubscribed(current_user_id)
    if subscription_flag:
        return render(request, 'home.html')
    else:
        return render(request,"not_subscribed.html")

#helper functions
# helper functions
@csrf_exempt
def isSubscribed(user_id):
	try:
		user_subscription_relation = UserSubscriptionRelation.objects.get(user_id=user_id).__dict__
		last_subscription_date = user_subscription_relation['last_subscription_date']
		current_date = timezone.now()
		if last_subscription_date < (current_date-timedelta(days=30)) :
			return False
		else:
			return True
	except Exception as e:
		print(e)
		print("Could not get subscription details. Contact admin")

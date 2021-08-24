from django.conf import settings
from .models import UserBankniftyFyersRelation as ubfr
import datetime
from datetime import timedelta
import pytz
from .main import StockMarket


def executeBankniftyOrders():
	from_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')) - timedelta(days=1)).replace(hour=15,minute=30,second=0)
	to_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata'))).replace(hour=9,minute=18,second=0)
	data = ubfr.objects.filter(date_added__gte=from_date,date_added__lte=to_date)
	print(data)
	print(from_date,to_date)
	for each_item in data.iterator():
		try:
			access_token = each_item.fyers_access_token
			number_of_lots = each_item.number_of_lots
			user = each_item.user_id
			algo_obj = StockMarket(access_token)
			order_id_1, order_id_2 = algo_obj.run(number_of_lots,user)
		except Exception as e:
			print(e)
			print('banknifty cron server problem')
			pass

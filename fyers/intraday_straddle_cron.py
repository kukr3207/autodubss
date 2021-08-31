from django.conf import settings
from .models import UserIntradayStraddleRelation as uisr
import datetime
from datetime import timedelta
import pytz
from .intraday_straddle import IntradayStraddle


def executeIntradayStraddleOrders():
	from_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')) - timedelta(days=1)).replace(hour=16,minute=0,second=0)
	to_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata'))).replace(hour=9,minute=55,second=0)
	data = uisr.objects.filter(date_added__gte=from_date,date_added__lte=to_date)
	for each_item in data.iterator():
		try:
			print("wertyujnbsrtyuikmbvd")
			access_token = each_item.fyers_access_token
			number_of_lots = each_item.number_of_lots
			stock = each_item.stock
			user = each_item.user_id
			algo_obj = IntradayStraddle(stock, access_token)
			algo_obj.run(number_of_lots)
		except Exception as e:
			print(e)
			print('intraday straddle cron server problem')
			pass

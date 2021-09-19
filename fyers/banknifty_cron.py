from django.conf import settings
from .models import UserBankniftyFyersRelation as ubfr
import datetime
from datetime import timedelta
import pytz
from .main import StockMarket
from truedata_ws.websocket.TD import TD

import multiprocessing

REALTIME_PORT = 8082
HISTORY_PORT = 8092
USERNAME = "FYERS1201"
PASSWORD = "4jV4JgKB"
HOLIDAY_LIST = ["26-01-2021", "11-03-2021", "29-03-2021", "02-04-2021", "14-04-2021", "21-04-2021", "13-05-2021", "21-07-2021", "19-08-2021", "10-09-2021" "15-10-2021", "05-11-2021", "19-11-2021", '03-01-2021', '10-01-2021', '17-01-2021', '24-01-2021', '31-01-2021', '07-02-2021', '14-02-2021', '21-02-2021', '28-02-2021', '07-03-2021', '14-03-2021', '21-03-2021', '28-03-2021', '04-04-2021', '11-04-2021', '18-04-2021', '25-04-2021', '02-05-2021', '09-05-2021', '16-05-2021', '23-05-2021', '30-05-2021', '06-06-2021', '13-06-2021', '20-06-2021', '27-06-2021', '04-07-2021', '11-07-2021', '18-07-2021', '25-07-2021', '01-08-2021', '08-08-2021', '15-08-2021', '22-08-2021', '29-08-2021', '05-09-2021', '12-09-2021', '19-09-2021', '26-09-2021', '03-10-2021', '10-10-2021', '17-10-2021', '24-10-2021', '31-10-2021', '07-11-2021', '14-11-2021', '21-11-2021', '28-11-2021', '05-12-2021', '12-12-2021', '19-12-2021', '26-12-2021', '02-01-2021', '09-01-2021', '16-01-2021', '23-01-2021', '30-01-2021', '06-02-2021', '13-02-2021', '20-02-2021', '27-02-2021', '06-03-2021', '13-03-2021', '20-03-2021', '27-03-2021', '03-04-2021', '10-04-2021', '17-04-2021', '24-04-2021', '01-05-2021', '08-05-2021', '15-05-2021', '22-05-2021', '29-05-2021', '05-06-2021', '12-06-2021', '19-06-2021', '26-06-2021', '03-07-2021', '10-07-2021', '17-07-2021', '24-07-2021', '31-07-2021', '07-08-2021', '14-08-2021', '21-08-2021', '28-08-2021', '04-09-2021', '11-09-2021', '18-09-2021', '25-09-2021', '02-10-2021', '09-10-2021', '16-10-2021', '23-10-2021', '30-10-2021', '06-11-2021', '13-11-2021', '20-11-2021', '27-11-2021', '04-12-2021', '11-12-2021', '18-12-2021', '25-12-2021']



def getPreviousDayValues(td_obj):
	try:
		end_date = datetime.datetime.today() - timedelta(days=1)
		hist_data = td_obj.get_historic_data("BANKNIFTY-I", end_time=end_date, duration='10 D', bar_size="EOD")
		previous_trading_date = (datetime.datetime.today() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) 
		previous_trading_date_str = datetime.datetime.strftime(previous_trading_date,"%d-%m-%Y")
		while previous_trading_date_str in HOLIDAY_LIST : 
			previous_trading_date = (previous_trading_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) 
			previous_trading_date_str = datetime.datetime.strftime(previous_trading_date,"%d-%m-%Y")
		for i in hist_data[::-1]:
			if True:
				pre_high = i["h"]
				pre_low = i["l"]
				pre_close = i["c"]
				wrong_previousday_values = 0
				break
			else:
				print("problem in previousdayvalues loop")
				wrong_previousday_values = 1
		print("Previous day high = {}, Previous day low = {}, Previous day close = {}".format(pre_high, pre_low, pre_close))
		print()
	except Exception as e:
		print("problem in previousdayvalues function")
		print(e)
		wrong_previousday_values = 1
	return  pre_high, pre_low, pre_close, wrong_previousday_values

def getPresentDayValue(td_obj):
	try:
		barsize = '1min'
		end_date = datetime.datetime.now()
		end_date = end_date.replace(hour=9, minute=16, second=0, microsecond=0) 
		today = datetime.datetime.strftime(end_date,"%d-%m-%Y")
		min_candle = 0
		if today not in HOLIDAY_LIST:
			hist_data = td_obj.get_historic_data("BANKNIFTY-I", end_time=end_date, duration='1 D', bar_size=barsize)
			for i in hist_data:
				if i["time"] == end_date:
					min_candle = i["c"]
					break
			print("Today 9:16 min candle close value = {}".format(min_candle))
			print()
			trading_holiday = 0
			wrong_presentday_values = 0
		else:
			print("Today is Nifty holiday/ weekend. Please comeback tomorrow")
			user_order_not_placed = 1
			user_order_not_placed_reason = "Today is Trading holiday."
	except Exception as e:
		print("error in presentdyvalues function")
		print(e)
		min_candle = 0
		wrong_presentday_values = 1
	return min_candle

def eachLoop(each_item):
	# try:
	access_token = each_item['fyers_access_token']
	number_of_lots = each_item['number_of_lots']
	user = each_item['user_id_id']
	algo_obj = StockMarket(
					access_token, 
					each_item['prev_high'], 
					each_item['pre_low'], 
					each_item['pre_close'],
					each_item['min_candle']
					)
	order_id_1, order_id_2 = algo_obj.run(number_of_lots,user)
	# except Exception as e:
	# 	print(e)
	# 	print('banknifty cron server problem')
	# 	pass

def executeBankniftyOrders():

	#get previousday and present day values
	td_obj = TD(USERNAME, PASSWORD)
	pre_high, pre_low, pre_close, wrong_previousday_values = getPreviousDayValues(td_obj)
	min_candle = getPresentDayValue(td_obj)

	from_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')) - timedelta(days=1)).replace(hour=15,minute=30,second=0)
	to_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')))#.replace(hour=9,minute=18,second=0)
	data = ubfr.objects.filter(date_added__gte=from_date,date_added__lte=to_date).values()
	list_data = []
	for each_record in data:
		each_record['prev_high'] = pre_high
		each_record['pre_low'] = pre_low
		each_record['pre_close'] = pre_close
		each_record['min_candle'] = min_candle
		list_data.append(each_record)
	pool_obj = multiprocessing.Pool(2)
	answer = pool_obj.map(eachLoop,list_data)
	# print(answer)







# def executeBankniftyOrders():
# 	from_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')) - timedelta(days=1)).replace(hour=15,minute=30,second=0)
# 	to_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')))#.replace(hour=9,minute=18,second=0)
# 	data = ubfr.objects.filter(date_added__gte=from_date,date_added__lte=to_date)
# 	print(data)
# 	print(from_date,to_date)
# 	for each_item in data.iterator():
# 		try:
# 			access_token = each_item.fyers_access_token
# 			number_of_lots = each_item.number_of_lots
# 			user = each_item.user_id
# 			algo_obj = StockMarket(access_token)
# 			order_id_1, order_id_2 = algo_obj.run(number_of_lots,user)
# 		except Exception as e:
# 			print(e)
# 			print('banknifty cron server problem')
# 			pass
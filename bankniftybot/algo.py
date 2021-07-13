# algorithm
from fyers_api import accessToken
from fyers_api import fyersModel

def fyersAuthentication():
	app_id = "VY1T8XB90T"
	app_secret = "V2FW23GWDW"
	app_session = accessToken.SessionModel(app_id, app_secret)
	response = app_session.auth()
	if response['code'] == 200:
		authorization_code = response['data']['authorization_code']
		app_session.set_token(authorization_code)
		token = app_session.generate_token()
		print(token)
		
	else:
		print("failed to genrate authorization_code")
		return 0

def runAlgorithm():
	fyersAuthentication()

import datetime
from datetime import  timedelta
# end_time=datetime(2021, 3, 5, 12, 30)

from truedata_ws.websocket.TD import TD
REALTIME_PORT = 8082
HISTORY_PORT = 8092
USERNAME = "FYERS1201"
PASSWORD = "4jV4JgKB"
# td_obj = TD(USERNAME, PASSWORD)

def getPreviousDayValues():
	# start_date = datetime.now() - timedelta(days=1)
	end_date = datetime.datetime.now() - timedelta(days=1)
	hist_data = td_obj.get_historic_data("BANKNIFTY-I", duration='10 D', bar_size="EOD", end_time=end_date)
	# pre_high = hist_data[-1]["h"]
	# pre_low = hist_data[-1]["l"]
	# pre_close = hist_data[-1]["c"]
	print(hist_data[-1])
	# print(pre_high, pre_low, pre_close)
	# return None
# getPreviousDayValues()

def getPresentDayValue():
	# today = datetime.date.today().strftime('%d-%m-%Y')
	# today = "18-06-2021"
	barsize = '1min'
	end_date = datetime.datetime.now()
	end_date = end_date.replace(hour=9, minute=16, second=0, microsecond=0)
	print(end_date)
	hist_data = td_obj.get_historic_data("BANKNIFTY-I", end_time=end_date, duration='1 D', bar_size=barsize)
	# print(hist_data)
	for i in hist_data:
		if i["time"] == end_date:
			print(i)
			self.min_candle = i["c"]
			break
	print("Today 9:16 min candle close value = {}".format(self.min_candle))
	print()
	exit()
	return None

from fyers_api import accessToken
import requests
import json
from fyers_api import fyersModel

def getAccessToken():
    url = 'https://api.fyers.in/api/v1/token'
    requestParams = {
    "fyers_id":"XC00383",
    "password":"Kishore@1973",
    "pan_dob":"10-05-1972",
    "appId":"VY1T8XB90T",
    "create_cookie":False}
    response = requests.post(url, json = requestParams )
    data = json.loads(response.text)["Url"]
    source = data.find("access_token=") + len("access_token=")
    access_token = data[source:]
    return access_token

def generateAccess():
    is_async = False #(By default False, Change to True for asnyc API calls.)
    fyers = fyersModel.FyersModel(is_async)
    return fyers

def placeOrder(access_token,fyers):
        try:
            response = fyers.place_orders(
            token = access_token,
            data = {
            "symbol" : "NSE:" + "BANKNIFTY21JUNFUT",
            "qty" : 1,
            "type" : 2,
            "side" : 1,
            "productType" : "INTRADAY",
            "limitPrice" : 420,
            "stopPrice" : 418,
            "disclosedQty" : 0,
            "validity" : "DAY",
            "offlineOrder" : "False",
            # "stopLoss" : 400,
            # "takeProfit" : 412
            }
            )

            print(response)
        except Exception as e:
            print(e)

# access_token = getAccessToken()
# fyers = generateAccess()
# placeOrder(access_token, fyers)

# def orderStatus():
	
print(datetime.datetime(2021, 6, 25) == datetime.datetime(2021, 6, 25, 0, 0, 0) )
print(datetime.datetime.today() - timedelta(days=1))

    def run2(self):
        self.newAuthorization()

    def newAuthorization(self):
        app_id = "VY1T8XB90T"
        app_secret = "V2FW23GWDW"
        app_session = accessToken.SessionModel(app_id, app_secret)
        response = app_session.auth()
        authorization_code = response['data']['authorization_code']
        app_session.set_token(authorization_code)
        url = app_session.generate_token()
        print(url)
        return (url)
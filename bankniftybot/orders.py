#import libraries
import requests
import json
from truedata_ws.websocket.TD import TD
import datetime
from datetime import timedelta
from fyers_api import accessToken

from fyers_api import fyersModel

def getAccessToken():
	url = 'https://api.fyers.in/api/v1/token'
	requestParams = {
	"fyers_id":"XC00383",
	"password":"Kishore@1973",
	"pan_dob":"10-05-1972",
	"appId":"VY1T8XB90T",
	"create_cookie":False}
	response = requests.post(url, json = requestParams)
	data = json.loads(response.text)["Url"]
	source = data.find("access_token=") + len("access_token=")
	access_token = data[source:]
	return access_token

def generateAccess():
    is_async = False #(By default False, Change to True for asnyc API calls.)
    fyers = fyersModel.FyersModel(is_async)
    return fyers



def placeOrder(access_token, fyers):
    try:
        response = fyers.place_orders(
        token = access_token,
        data = {
        "symbol" : "NSE:" + "SBIN21JUNFUT",
        "qty" : 1,
        "type" : 1,
        "side" : 1,
        "productType" : "BO",
        "limitPrice" : 418,
        "stopPrice" : 417,
        "disclosedQty" : 0,
        "validity" : "DAY",
        "offlineOrder" : "False",
        "stopLoss" : 10,
        "takeProfit" : 10,
        }
        )
        print(response)
    except Exception as e:
        print(e)

access_token = getAccessToken()
fyers = generateAccess()
placeOrder(access_token, fyers)
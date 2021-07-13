from .models import UserLotsInput
from django.db.models import Q
import datetime
from datetime import timedelta
from django.utils import timezone
import json
from fyers_api import fyersModel
from fyers_api import accessToken
import requests

def getAccessToken():
    try:
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
        accesstoken_exception = 0
        return access_token, accesstoken_exception
    except Exception as e:
        print("Error in getAccessToken")
        print(e)
        access_token = None
        accesstoken_exception = 1
        return access_token, accesstoken_exception

def generateAccess():
    try:
        is_async = False #(By default False, Change to True for asnyc API calls.)
        fyers = fyersModel.FyersModel(is_async)
        generateaccess_exception = 0
        return fyers, generateaccess_exception
    except:
        generateaccess_exception = 1
        fyers = None
        return fyers, generateaccess_exception

def getOrderStatus(order_id, access_token):
    try:
        response = fyers.order_status(
                        token = access_token,
                        data = {
                        "id" : order_id
                        }
                        )
        
    except Exception as e:
        print("Cannot get order status. cron jobs")
        print(e)

def cancelOrdersAt1430():
    current_time = timezone.now()
    today_time = current_time.replace(hour=9, minute=16, second=0, microsecond=0)
    data = UserLotsInput.objects.filter(Q(date_added__range = [today_time, current_time]))
    for each_field in data.iterator():
        order_id_1 = each_field.order_id_1
        order_id_2 = each_field.order_id_2


    


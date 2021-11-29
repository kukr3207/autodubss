from django.db import connection
import pytz
import datetime
from datetime import timedelta

from .place_order import placeOrder
from .main import BNFuturesBot
from .variables import *
from home.models import UserBNFuturesRelation as ubfr

def executeBNFuturesOrder():
    #get values
    bn_futures_bot_obj = BNFuturesBot()
    order_1, order_2 = bn_futures_bot_obj.logic()
    # loop each form record and place orders
    from_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')) - timedelta(days=1)).replace(hour=15,minute=30,second=0)
    to_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')))#.replace(hour=9,minute=18,second=0)
    from_date = from_date.strftime("%Y-%m-%d %H:%M:%S")
    to_date = to_date.strftime("%Y-%m-%d %H:%M:%S")
    cursor = connection.cursor()
    query = """select ubfr.number_of_lots, ubfr.fyers_access_token , ufr.fyers_app_id
            from home_userbnfuturesrelation as ubfr
            join home_userfyersapprelation as ufr
            on ubfr.user_id_id = ufr.user_id
            """
    # query = "select * from home_userfyersapprelation"
    cursor.execute(query)
    data = cursor.fetchall()
    print("--------------------------------------")
    # print(data)
    # print(cursor.description)
    for each_record in data:
        quantity = each_record[0]#['number_of_lots']
        fyers_app_id = each_record[2]
        fyers_acces_token = each_record[1]
        if order_1 !=0 :
            difference = order_1['difference']
            order_value = order_1['order_value']
            order_value = int(order_value) + 30
            side = order_1['side']
            placeOrder(BN_FUTURES_CONTRACT,difference,quantity,order_value,side,fyers_app_id, fyers_acces_token)
        if order_2 !=0 :
            difference = order_2['difference']
            order_value = order_2['order_value']
            order_value = int(order_value) - 30
            side = order_2['side']
            placeOrder(BN_FUTURES_CONTRACT,difference,quantity,order_value,side,fyers_app_id, fyers_acces_token)  

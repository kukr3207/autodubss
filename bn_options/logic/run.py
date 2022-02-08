from django.db import connection
import pytz
import datetime
from datetime import timedelta

from .place_order import placeOrder, exitOrder
from .main import BNOptionsBot
from bn_options.models import OptionsOrdersDetails,BNOptionsBotOrders
from .variables import *
from home.models import UserBNOptionsRelation as ubor

def executeBNOptionsOrder():
    #get values
    bn_options_bot_obj = BNOptionsBot()
    order = bn_options_bot_obj.logic()
    # loop each form record and place orders
    from_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')) - timedelta(days=1)).replace(hour=15,minute=30,second=0)
    to_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')))#.replace(hour=9,minute=18,second=0)
    from_date = from_date.strftime("%Y-%m-%d %H:%M:%S")
    to_date = to_date.strftime("%Y-%m-%d %H:%M:%S")
    cursor = connection.cursor()
    query = """select ubor.number_of_lots, ubor.fyers_access_token , ufr.fyers_app_id, ubor.user_id
            from home_userbnoptionsrelation as ubor
            join home_userfyersapprelation as ufr
            on ubor.id = ufr.id
            """
    cursor.execute(query)
    data = cursor.fetchall()
    # print(cursor.description)
    data = BNOptionsBotOrders.objects.get(dummy_id=1)
    for each_record in data:
        contract = each_record[1]
    contract = BNOptionsBotOrders.objects.get(dummy_id=1)
    for each_record in data:
        quantity = each_record[0]#['number_of_lots']
        fyers_app_id = each_record[2]
        fyers_acces_token = each_record[1]
        user_id = each_record[3]
        if order !=0 :
            order_value = order['order_value']
            response = placeOrder(contract,quantity,order_value, fyers_app_id, fyers_acces_token)
            db_obj, created = OptionsOrdersDetails.objects.get_or_create(user_id=user_id)
            db_obj.order_id = response['id']
            db_obj.code = response['code']
            db_obj.message = response['message']
            db_obj.is_active = 1
            db_obj.save()

def exitBNOptionsOrder(self):
    # data = OptionsOrdersDetails.objects.get(is_active=1)
    cursor = connection.cursor()
    query = """select ubor.fyers_access_token , ufr.fyers_app_id, ood.order_id
                from home_userbnoptionsrelation as ubor
                join home_userfyersapprelation as ufr
                on ubor.id = ufr.id
                join bn_options_optionsordersdetails as ood
                on ubor.id = ood.id
                where ood.is_active = 1
                """
    cursor.execute(query)
    data = cursor.fetchall()
    for each_record in data:
        fyers_app_id = each_record[1]
        fyers_acces_token = each_record[0]
        order_id = each_record[2]
        response = exitOrder(order_id,fyers_app_id,fyers_acces_token)
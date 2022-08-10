from truedata_ws.websocket.TD import TD
import datetime
from datetime import timedelta

from .variables import *
from bn_futures.models import BNFuturesBotOrders

class BNFuturesBot():
    def __init__(self):
        pass

    def getPreviousDayValues(self,td_obj):
        end_date = datetime.datetime.today() - timedelta(days=1)
        hist_data = td_obj.get_historic_data(BN_FUTURES_CONTRACT_FETCH_VALUES,end_time=end_date,duration='5 D',bar_size="EOD")
        print("*******333#############")
        print(hist_data)
        previousday_high = hist_data[::-1]['h']
        previousday_low = hist_data[::-1]['l']
        previousday_close = hist_data[::-1]['c']
        return previousday_high, previousday_low, previousday_close

    def getPresentDayValues(self,td_obj):
        # end_date = datetime.datetime.now().replace(hour=9, minute=16, second=0, microsecond=0) 
        end_date = (datetime.datetime.today()).replace(hour=9, minute=16, second=0, microsecond=0) 
        hist_data = td_obj.get_historic_data("BANKNIFTY-I", end_time=end_date, duration='1 D', bar_size='1min')
        for each_value in hist_data:
            if each_value['time'] == end_date:
                today_916_close = each_value['c']
                break
        return today_916_close

    def logic(self):
        # td_obj = TD(USERNAME, PASSWORD)
        # previousday_high,previousday_low,previousday_close = self.getPreviousDayValues(td_obj)
        # today_916_close = self.getPresentDayValues(td_obj)
        # td_obj.disconnect()
        # print("********************************")
        # print(previousday_high,previousday_low,previousday_close)
        previousday_high = 36675
        previousday_low = 36468
        previousday_close = 36490
        today_916_close = 36508
        # calculating op_values
        op_values = {}
        op_values["rev_sell"] = previousday_close - (0.6 * (previousday_high - previousday_low))
        op_values["buy"] = previousday_close - (0.26 * (previousday_high - previousday_low)) 
        op_values["sell"] = 0.26 * (previousday_high - previousday_low) + previousday_close 
        op_values["rev_buy"] = 0.6 * (previousday_high - previousday_low) + previousday_close 
        # decission function
        if today_916_close <= op_values["rev_sell"]:
            order_1, order_2 = self.senerio1(op_values)
        elif today_916_close > op_values["rev_sell"] and today_916_close <= op_values["buy"]:
            order_1, order_2 = self.senerio2(op_values)
        elif today_916_close > op_values["buy"] and today_916_close <= op_values["sell"]:
            order_1, order_2  = self.senerio3(op_values)
        elif today_916_close > op_values["sell"] and today_916_close <= op_values["rev_buy"]:
            order_1, order_2 = self.senerio4(op_values)
        elif today_916_close > op_values["rev_buy"]:
            order_1, order_2 = self.senerio5(op_values)
        print(order_1)
        print(order_2)
        #save order values in db
        # db_obj, created = BNFuturesBotOrders.objects.get_or_create(dummy_id=1)
        # if order_1 == 0:
        #     db_obj.order_value_1 = 0
        #     db_obj.side_1 = 0
        #     db_obj.difference_1 = 0
        # else:
        #     db_obj.order_value_1 = order_1['order_value']
        #     db_obj.side_1 = order_1['side']
        #     db_obj.difference_1 = order_1['difference']
        # if order_2 == 0:
        #     db_obj.order_value_2 = 0
        #     db_obj.side_2 = 0
        #     db_obj.difference_2 = 0
        # else:
        #     db_obj.order_value_2 = order_2['order_value']
        #     db_obj.side_2 = order_2['side']
        #     db_obj.difference_2 = order_2['difference']
        # db_obj.save()
        return order_1, order_2

    def senerio1(self,op_values):
        order_1 = {}
        order_1['difference'] = abs(op_values["buy"] - op_values["rev_sell"])
        order_1['order_value'] = op_values["rev_sell"] 
        order_1['side'] = -1
        order_2 = 0
        return order_1, order_2

    def senerio2(self,op_values):
        order_1 = {}
        order_1['difference'] = abs(op_values["buy"] - op_values["rev_sell"])
        order_1['order_value'] = op_values["rev_sell"] 
        order_1['side'] = -1
        order_2 = {}
        order_2['difference'] = abs(op_values["buy"] - op_values["rev_sell"])
        order_2['order_value'] = op_values["buy"]
        order_2['side'] = 1
        return order_1, order_2

    def senerio3(self,op_values):
        order_1 = {}
        order_1['difference'] = abs(op_values["rev_buy"] - op_values["sell"])
        order_1['order_value'] = op_values["sell"]
        order_1['side'] = -1
        order_2 = {}
        order_2['difference'] = abs(op_values["buy"] - op_values["rev_sell"])
        order_2['order_value'] = op_values["buy"] 
        order_2['side'] = 1
        return order_1, order_2

    def senerio4(self,op_values):
        order_1 = {}
        order_1['difference'] = abs(op_values["rev_buy"] - op_values["sell"])
        order_1['order_value'] = op_values["sell"] 
        order_1['side'] = -1
        order_2 = {}
        order_2['difference'] = abs(op_values["rev_buy"] - op_values["sell"])
        order_2['order_value'] = op_values["rev_buy"]
        order_2['side'] = 1
        return order_1, order_2

    def senerio5(self,op_values):
        order_1 = 0
        order_2 = {}
        order_2['difference'] = abs(op_values["rev_buy"] - op_values["sell"])
        order_2['order_value'] = op_values["rev_buy"]
        order_2['side'] = 1
        return order_1, order_2  


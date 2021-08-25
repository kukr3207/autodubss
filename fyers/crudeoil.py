import schedule
import time
import requests
import json
from truedata_ws.websocket.TD import TD
import datetime
from datetime import timedelta
from fyers_api import accessToken
from fyers_api import fyersModel

REALTIME_PORT = 8082
HISTORY_PORT = 8092
USERNAME = "FYERS1201"
PASSWORD = "4jV4JgKB"

class CrudeoilBot():
    def __init__(self, access_token):
        self.pre_high = 0
        self.pre_low = 0
        self.pre_close = 0 
        self.previous_day_barsize = "EOD"
        self.stock = "CRUDEOIL-I"

        self.access_token = access_token

        # Exception Handling
        self.accesstoken_exception = 1
        self.generateaccess_exception = 1
        self.wrong_previousday_values = 1
        self.wrong_presentday_values = 1
        self.wrong_opvalues = 1
        self.trading_holiday = 1
        self.decissionProblem = 1
        self.place_order_error = 1
        self.user_order_not_placed = 1
        self.fyers_order_executed_message = ""
        self.user_order_not_placed_reason = ""

    def generateAccess(self):
        try:
            is_async = False #(By default False, Change to True for asnyc API calls.)
            fyers = fyersModel.FyersModel(is_async)
            self.generateaccess_exception = 0
            return fyers
        except:
            self.generateaccess_exception = 1
    def getPreviousDayValues(self,td_obj):
        try:
            end_date = datetime.datetime.today() - timedelta(days=1)
            hist_data = td_obj.get_historic_data(self.stock, end_time=end_date, duration='10 D', bar_size=self.previous_day_barsize)
            sorted_hist_data = sorted(hist_data, key = lambda i: i['time'],reverse=True)
            print(sorted_hist_data)
            self.pre_high = sorted_hist_data[0]['h']
            self.pre_low = sorted_hist_data[0]['l']
            self.pre_close = sorted_hist_data[0]['c']
            self.wrong_previousday_values = 0
        except Exception as e:
            print("problem in previousdayvalues crudeoil function")
            print(e)
            self.wrong_previousday_values = 1
        return True

    def decissionFunction(self,quantity, fyers):
        try:
            #buy order
            buy_value = self.pre_close + (0.33*(self.pre_high - self.pre_low))
            difference = 40
            stop_difference = 25
            order_value = buy_value
            side = 1
            order_id_1 = self.placeOrder(difference, stop_difference, quantity, order_value, side, fyers)

            #sell order
            sell_value = self.pre_close - (0.33*(self.pre_high - self.pre_low))
            difference = 40
            stop_difference = 25
            order_value = sell_value
            side = -1
            order_id_2 = self.placeOrder(difference, stop_difference, quantity, order_value, side, fyers)
        except Exception as e:
            print(e)
            print("Crudeoil Bot is undable make decission")
            order_id_1 = 0
            order_id_2 = 0
        return order_id_1, order_id_2

    """
    These functions are for placing, cancelling  the  order
    """
    def placeOrder(self, difference, stop_difference, quantity, order_value, side, fyers):
        try:
            number_of_stocks = quantity  # no need to multiply by 25 
            if side > 0:
                stop_price = int(order_value) - 1
            else:
                stop_price = int(order_value) + 1
            response = fyers.place_orders(
                token = self.access_token,
                data = {
                    "symbol" : "MCX:" + "CRUDEOIL21SEPFUT",
                    "qty" : number_of_stocks,
                    "type" : 4,
                    "side" : side,
                    "productType" : "BO",
                    "limitPrice" : int(order_value),
                    "stopPrice" : int(stop_price),    
                    "disclosedQty" : 0,
                    "validity" : "DAY",
                    "offlineOrder" : "False",
                    "stopLoss" : int(stop_difference),
                    "takeProfit" : int(difference),
                    }
                )
            print(response)
            self.fyers_order_executed_message = response['message']
            #handling the response
            if response is None:
                print("Something worng with placing order. place order response is None")
                self.place_order_error = 1
                return 0
            elif response['code'] != 200:
                print("Something worng with placing order. place ordr response is None")
                print("place order code is: %s"%(response['code']))
                self.place_order_error = 1
                return 0
            elif response['code'] == 200:
                order_id = response['data']['id']
                return order_id
        except Exception as e:
            print(e)
            return 0

    def run(self, quantity, user):
        # self.getAccessToken()
        fyers = self.generateAccess()
        # if self.accesstoken_exception == 0 and self.generateaccess_exception == 0:
        if self.access_token:
            td_obj = TD(USERNAME, PASSWORD)
            self.getPreviousDayValues(td_obj)
            td_obj.disconnect()
        else:
            self.user_order_not_placed = 1
            self.user_order_not_placed_reason = "Problem in fetching previousday crudeoil price"
            order_id_1 = 0
            order_id_2 = 0
            return order_id_1, order_id_2
        if self.wrong_previousday_values == 0:
            # self.closeOtherOrderIfOneExecutes(user)
            order_id_1, order_id_2  = self.decissionFunction(quantity, fyers)
            return order_id_1, order_id_2
        else:
            self.user_order_not_placed = 1
            self.user_order_not_placed_reason = "Algorithm is unable to make decission"
            order_id_1 = 0
            order_id_2 = 0
            return order_id_1, order_id_2


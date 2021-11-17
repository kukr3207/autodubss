#import libraries
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

HOLIDAY_LIST = ["26-01-2021", "11-03-2021", "29-03-2021", "02-04-2021", "14-04-2021", "21-04-2021", "13-05-2021", "21-07-2021", "19-08-2021", "10-09-2021" "15-10-2021", "05-11-2021", "19-11-2021", '03-01-2021', '10-01-2021', '17-01-2021', '24-01-2021', '31-01-2021', '07-02-2021', '14-02-2021', '21-02-2021', '28-02-2021', '07-03-2021', '14-03-2021', '21-03-2021', '28-03-2021', '04-04-2021', '11-04-2021', '18-04-2021', '25-04-2021', '02-05-2021', '09-05-2021', '16-05-2021', '23-05-2021', '30-05-2021', '06-06-2021', '13-06-2021', '20-06-2021', '27-06-2021', '04-07-2021', '11-07-2021', '18-07-2021', '25-07-2021', '01-08-2021', '08-08-2021', '15-08-2021', '22-08-2021', '29-08-2021', '05-09-2021', '12-09-2021', '19-09-2021', '26-09-2021', '03-10-2021', '10-10-2021', '17-10-2021', '24-10-2021', '31-10-2021', '07-11-2021', '14-11-2021', '21-11-2021', '28-11-2021', '05-12-2021', '12-12-2021', '19-12-2021', '26-12-2021', '02-01-2021', '09-01-2021', '16-01-2021', '23-01-2021', '30-01-2021', '06-02-2021', '13-02-2021', '20-02-2021', '27-02-2021', '06-03-2021', '13-03-2021', '20-03-2021', '27-03-2021', '03-04-2021', '10-04-2021', '17-04-2021', '24-04-2021', '01-05-2021', '08-05-2021', '15-05-2021', '22-05-2021', '29-05-2021', '05-06-2021', '12-06-2021', '19-06-2021', '26-06-2021', '03-07-2021', '10-07-2021', '17-07-2021', '24-07-2021', '31-07-2021', '07-08-2021', '14-08-2021', '21-08-2021', '28-08-2021', '04-09-2021', '11-09-2021', '18-09-2021', '25-09-2021', '02-10-2021', '09-10-2021', '16-10-2021', '23-10-2021', '30-10-2021', '06-11-2021', '13-11-2021', '20-11-2021', '27-11-2021', '04-12-2021', '11-12-2021', '18-12-2021', '25-12-2021']

# Estabishing truedata connection

class StockMarket:

    def __init__(self, access_token, pre_high, pre_low, pre_close, min_candle, fyers_id=None, fyers_password=None, fyers_pan_dob=None):
        self.previous_day_barsize = "EOD"
        parameters = {}
        self.pre_high = pre_high
        self.pre_low = pre_low
        self.pre_close = pre_close
        self.min_candle = min_candle
        self.share = parameters.get("share", "BANKNIFTY-I")
        self.qty = parameters.get("qty", 1)
        self.access_token = access_token

        self.buy_value = None 
        self.target = None 
        self.stop_loss = None 
        self.lost = None 

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

        #fyers credentials
        self.fyers_id = fyers_id
        self.fyers_password = fyers_password
        self.fyers_pan_dob = fyers_pan_dob

    """
    getAccessToken, generateAccess are used to place order.
    """
    def getAccessToken(self):
        try:
            url = 'https://api.fyers.in/api/v1/token'
            requestParams = {
            "fyers_id":'XC00383',#self.fyers_id,
            "password":'Kishore@1126',#self.fyers_password,
            "pan_dob":'10-05-1972',#self.fyers_pan_dob,
            "appId":"VY1T8XB90T",
            "create_cookie":False}
            response = requests.post(url, json = requestParams )
            print(response)
            data = json.loads(response.text)["Url"]
            source = data.find("access_token=") + len("access_token=")
            self.access_token = data[source:]
            self.accesstoken_exception = 0

        except Exception as e:
            print("Error in getAccessToken")
            print(e)
            self.accesstoken_exception = 1

    def generateAccess(self):
        try:
            is_async = False #(By default False, Change to True for asnyc API calls.)
            fyers = fyersModel.FyersModel(is_async)
            self.generateaccess_exception = 0
            return fyers
        except:
            self.generateaccess_exception = 1

    """
    getPreviousDayValues, getPresentDayValue are used to get historic data.
    """
    def getPreviousDayValues(self,td_obj):
        try:
            end_date = datetime.datetime.today() - timedelta(days=1)
            hist_data = td_obj.get_historic_data(self.share, end_time=end_date, duration='10 D', bar_size=self.previous_day_barsize)
            previous_trading_date = (datetime.datetime.today() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) 
            previous_trading_date_str = datetime.datetime.strftime(previous_trading_date,"%d-%m-%Y")
            while previous_trading_date_str in HOLIDAY_LIST : 
                previous_trading_date = (previous_trading_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) 
                previous_trading_date_str = datetime.datetime.strftime(previous_trading_date,"%d-%m-%Y")
            for i in hist_data[::-1]:
                if True:
                    self.pre_high = i["h"]
                    self.pre_low = i["l"]
                    self.pre_close = i["c"]
                    self.wrong_previousday_values = 0
                    print(i)
                    break
                else:
                    print("problem in previousdayvalues loop")
                    self.wrong_previousday_values = 1
            print("Previous day high = {}, Previous day low = {}, Previous day close = {}".format(self.pre_high, self.pre_low, self.pre_close))
            print()
        except Exception as e:
            print("problem in previousdayvalues function")
            print(e)
            self.wrong_previousday_values = 1

        return None         

    # def getPreviousDayCrudeoilValues(self, td_obj):
    #     try:
    #        end_date = datetime.datetime.today() - timedelta(days=1)


    def getPresentDayValue(self,td_obj):
        try:
            barsize = '1min'
            end_date = datetime.datetime.now()
            end_date = end_date.replace(hour=9, minute=16, second=0, microsecond=0) 
            today = datetime.datetime.strftime(end_date,"%d-%m-%Y")
            if today not in HOLIDAY_LIST:
                hist_data = td_obj.get_historic_data(self.share, end_time=end_date, duration='1 D', bar_size=barsize)
                for i in hist_data:
                    if i["time"] == end_date:
                        self.min_candle = i["c"]
                        break
                print("Today 9:16 min candle close value = {}".format(self.min_candle))
                print()
                self.trading_holiday = 0
                self.wrong_presentday_values = 0
            else:
                print("Today is Nifty holiday/ weekend. Please comeback tomorrow")
                self.user_order_not_placed = 1
                self.user_order_not_placed_reason = "Today is Trading holiday."
        except Exception as e:
            print("error in presentdyvalues function")
            print(e)
            self.wrong_presentday_values = 1

        return None

    """
    These functions are for placing, cancelling  the  order
    """
    def placeOrder(self, difference, quantity,  target, stop_loss, order_value, side, fyers):
        try:
            number_of_stocks = quantity*25  #banknifty lot size is in 25 multiples. 
            if side > 0:
                stop_price = int(order_value) - 2
            else:
                stop_price = int(order_value) + 1
            response = fyers.place_orders(
                token = self.access_token,
                data = {
                    "symbol" : "NSE:" + "BANKNIFTY21NOVFUT",
                    "qty" : number_of_stocks,
                    "type" : 4,
                    "side" : side,
                    "productType" : "BO",
                    "limitPrice" : int(order_value),
                    "stopPrice" : int(stop_price),    
                    "disclosedQty" : 0,
                    "validity" : "DAY",
                    "offlineOrder" : "False",
                    "stopLoss" : int(difference),
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

    def getOrderStatus(self, orderId, fyers):
        response = fyers.order_status(
            token = self.access_token,
            data = {
            "id" : orderId
            }
            )
        return response

    def cancelOrder(self,orderId,fyers):
        response = fyers.delete_orders(
            token = self.access_token,
            data = {
            "id" : orderId
            }
            )
        return response

    def closeOtherOrderIfOneExecutes(self,user, fyers):
        response_1 = 0
        response_2 = 0
        today_min = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        today_max = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
        db_records = UserLotsInput.objects.filter(user_id=user.id, date_added__range=(today_min, today_max))
        number_of_records = 0
        for each_record in db_records.iterator():
            order_id_1 = each_record.order_id_1
            order_id_2 = each_record.order_id_2
            res_1 = self.getOrderStatus(order_id_1,fyers)
            res_2 = self.getOrderStatus(order_id_2,fyers)
            number_of_records += 1
        if number_of_records == 0 :
            return False
        if response_1 == 0 or response_2 == 0 :
            return False
        else:
            if res_1['code'] == 200 and res_2['code']==200:
                order_id_1_status = res_1['data']['orderDetails']['status']
                order_id_2_status = res_2['data']['orderDetails']['status']
                if order_id_1_status == 6 and order_id_2_status != 6:
                    cancelOrder(order_id_1, fyers)
                    return True
                elif order_id_2_status == 6 and order_id_1_status != 6:
                    cancelOrder(order_id_2, fyers)
                    return True
            else:
                return False
    
    """
    BankNiftyBot Algorithm functions 
    """
    def calculateOPValues(self):
        try:
            op_values = {}
            op_values["rev_sell"] = self.pre_close - (0.6 * (self.pre_high - self.pre_low))
            op_values["buy"] = self.pre_close - (0.26 * (self.pre_high - self.pre_low))
            op_values["sell"] = 0.26 * (self.pre_high - self.pre_low) + self.pre_close
            op_values["rev_buy"] = 0.6 * (self.pre_high - self.pre_low) + self.pre_close

            print("Reverse sell = {}, Buy = {}, Sell = {}, Reverse Buy {}".format(op_values["rev_sell"], op_values["buy"], op_values["sell"], op_values["rev_buy"]))
            print()
            self.wrong_opvalues = 0
        except Exception as e:
            print("error in calculateOPValues function")
            print(e)
            self.wrong_opvalues = 1
        return op_values

    def decissionFunction(self, op_values, quantity, fyers):
        try:
            if self.min_candle <= op_values["rev_sell"]:
                order_id_1, order_id_2 = self.senerio1(op_values, quantity, fyers)
            elif self.min_candle > op_values["rev_sell"] and self.min_candle <= op_values["buy"]:
                order_id_1, order_id_2 = self.senerio2(op_values, quantity, fyers)
            elif self.min_candle > op_values["buy"] and self.min_candle <= op_values["sell"]:
                order_id_1, order_id_2  = self.senerio3(op_values, quantity, fyers)
            elif self.min_candle > op_values["sell"] and self.min_candle <= op_values["rev_buy"]:
                order_id_1, order_id_2 = self.senerio4(op_values, quantity, fyers)
            elif self.min_candle > op_values["rev_buy"]:
                order_id_1, order_id_2 = self.senerio5(op_values, quantity, fyers)
        except Exception as e:
            print("Problem in decissionFunction")
            print(e)
            self.decissionProblem = 1
            order_id_1 = 0
            order_id_2 = 0
        return order_id_1, order_id_2 

    def senerio1(self, op_values, quantity, fyers):
        try:
            difference = abs(op_values["buy"] - op_values["rev_sell"])
            target = abs(op_values["rev_sell"] - difference)
            stop_loss = op_values["buy"]
            order_value = op_values["rev_sell"]
            side = -1
            print("Senerio - 1: Difference {},  target = {}, stop loss = {},  order place = {}".format(difference, target, stop_loss, order_value))
            print()
            order_id_1 = self.placeOrder(difference, quantity, target, stop_loss, order_value, side, fyers)
            order_id_2 = 0
        except Exception as e:
            print("Senerio 1 triggered but not executed")
            print(e)
            order_id_1 = 0
            order_id_2 = 0
        return order_id_1, order_id_2

    def senerio2(self, op_values, quantity, fyers):
        try:
            difference = abs(op_values["buy"] - op_values["rev_sell"])
            target = abs(op_values["rev_sell"] - difference)
            stop_loss = op_values["buy"]
            order_value = op_values["rev_sell"]  
            side = -1
            print("Senerio - 2 (limit order 1): Difference {},  target = {}, stop loss = {},  order place = {}".format(difference, target, stop_loss, order_value))
            print()
            order_id_1 = self.placeOrder(difference, quantity, target, stop_loss, order_value, side, fyers)
            
            difference = abs(op_values["buy"] - op_values["rev_sell"])
            target = abs(op_values["buy"] + difference)
            stop_loss = op_values["rev_sell"]
            order_value = op_values["buy"] 
            side = 1
            print("Senerio - 2 (limit order 2): Difference {},  target = {}, stop loss = {},  order place = {}".format(difference, target, stop_loss, order_value))
            print()
            order_id_2 = self.placeOrder(difference, quantity, target, stop_loss, order_value, side, fyers)
        except Exception as e:
            print("Senerio 2 triggered but not executed")
            print(e)
            order_id_1 = 0
            order_id_2 = 0
        return order_id_1, order_id_2

    def senerio3(self, op_values, quantity, fyers):
        try:
            difference = abs(op_values["buy"] - op_values["rev_sell"])
            target = abs(op_values["buy"] - difference)
            stop_loss = op_values["rev_sell"]
            order_value = op_values["buy"]  
            side = 1
            print("Senerio - 3 (limit order 1): Difference {},  target = {}, stop loss = {},  order place = {}".format(difference, target, stop_loss, order_value))
            print()
            order_id_1 = self.placeOrder(difference, quantity, target, stop_loss, order_value, side, fyers)


            difference = abs(op_values["rev_buy"] - op_values["sell"])
            target = abs(op_values["sell"] + difference)
            stop_loss =  op_values["rev_buy"]
            order_value = op_values["sell"]  
            side = -1
            print("Senerio - 3 (limit order 2): Difference {},  target = {}, stop loss = {},  order place = {}".format(difference, target, stop_loss, order_value))
            print()
            order_id_2 = self.placeOrder(difference, quantity, target, stop_loss, order_value, side, fyers)
        except Exception as e:
            print("Senerio 3 triggered but not executed")
            print(e)
            order_id_1 = 0
            order_id_2 = 0
        return order_id_1, order_id_2

    def senerio4(self, op_values, quantity, fyers):
        try:
            difference = abs(op_values["rev_buy"] - op_values["sell"])
            target = abs(op_values["sell"] - difference)
            stop_loss =  op_values["rev_buy"]
            order_value = op_values["sell"]  
            side = -1
            print("Senerio - 4 (limit order 1): Difference {},  target = {}, stop loss = {},  order place = {}".format(difference, target, stop_loss, order_value))
            print()
            order_id_1 = self.placeOrder(difference, quantity, target, stop_loss, order_value, side, fyers)

            difference = abs(op_values["rev_buy"] - op_values["sell"])
            target = abs(op_values["rev_buy"] + difference)
            stop_loss =  op_values["sell"]
            order_value = op_values["rev_buy"]  
            side = 1
            print("Senerio - 4 (limit order 2): Difference {},  target = {}, stop loss = {},  order place = {}".format(difference, target, stop_loss, order_value))
            print()
            order_id_2 = self.placeOrder(difference, quantity, target, stop_loss, order_value, side, fyers)
        except Exception as e:
            print("Senerio 4 triggered but not executed")
            print(e)
            order_id_1 = 0
            order_id_2 = 0
        return order_id_1, order_id_2

    def senerio5(self, op_values, quantity, fyers):
        try:
            difference = abs(op_values["rev_buy"] - op_values["sell"])
            target = abs(op_values["rev_buy"] + difference)
            stop_loss =  op_values["sell"]
            order_value = op_values["rev_buy"]  
            side = 1
            print("Senerio - 5: Difference {},  target = {}, stop loss = {},  order place = {}".format(difference, target, stop_loss, order_value))
            print()
            order_id_1 = self.placeOrder(difference, quantity, target, stop_loss, order_value, side, fyers)
            order_id_2 = 0
        except Exception as e:
            print("Senerio 5 triggered but not executed")
            print(e)
            order_id_1 = 0
            order_id_2 = 0
        return order_id_1, order_id_2

    
    def run(self, quantity, user):
        # self.getAccessToken()
        fyers = self.generateAccess()
        # if self.accesstoken_exception == 0 and self.generateaccess_exception == 0:
        if self.access_token:
            # td_obj = TD(USERNAME, PASSWORD)
            # self.getPreviousDayValues(td_obj)
            # self.getPresentDayValue(td_obj)
            # td_obj.disconnect()
            pass
        else:
            self.user_order_not_placed = 1
            self.user_order_not_placed_reason = "Problem in fetching previousday and presentday price"
            order_id_1 = 0
            order_id_2 = 0
            return order_id_1, order_id_2
        if self.min_candle != 0:
            op_values = self.calculateOPValues()
        else:
            self.user_order_not_placed = 1
            self.user_order_not_placed_reason = "Problem in algorithm"
            order_id_1 = 0
            order_id_2 = 0
            return order_id_1, order_id_2
        if self.wrong_opvalues == 0:
            # self.closeOtherOrderIfOneExecutes(user)
            order_id_1, order_id_2  = self.decissionFunction(op_values, quantity, fyers)
            return order_id_1, order_id_2
        else:
            self.user_order_not_placed = 1
            self.user_order_not_placed_reason = "Algorithm is unable to make decission"
            order_id_1 = 0
            order_id_2 = 0
            return order_id_1, order_id_2

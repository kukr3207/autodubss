import datetime
from fyers_api import accessToken
from fyers_api import fyersModel

class BNOptionsBuyingBot():

    def __init__(self, access_token, pre_high, pre_low, pre_close, min_candle, atm_strikeprice, atm_ce_value, atm_pe_value, no_of_lots, WEEKLY_CONTRACT_DATE):
        self.access_token = access_token
        self.pre_close = pre_close
        self.pre_high = pre_high
        self.pre_low = pre_low
        self.min_candle = min_candle
        self.atm_strikeprice = atm_strikeprice
        self.weekly_contract_date = WEEKLY_CONTRACT_DATE
        self.atm_ce_value = atm_ce_value
        self.atm_pe_value = atm_pe_value
        self.no_of_lots = no_of_lots

    def generateAccess(self):
        is_async = False #(By default False, Change to True for asnyc API calls.)
        fyers = fyersModel.FyersModel(is_async)
        self.generateaccess_exception = 0
        return fyers

    def calculateOPValues(self):
        op_values = {}
        op_values["rev_sell"] = self.pre_close - (0.6 * (self.pre_high - self.pre_low))
        op_values["buy"] = self.pre_close - (0.26 * (self.pre_high - self.pre_low))
        op_values["sell"] = 0.26 * (self.pre_high - self.pre_low) + self.pre_close
        op_values["rev_buy"] = 0.6 * (self.pre_high - self.pre_low) + self.pre_close
        print("Reverse sell = {}, Buy = {}, Sell = {}, Reverse Buy {}".format(op_values["rev_sell"], op_values["buy"], op_values["sell"], op_values["rev_buy"]))
        print()
        return op_values

    def decissionFunction(self, op_values, quantity, fyers):
        if self.min_candle <= op_values["rev_sell"]:
            self.senerio1(op_values, quantity, fyers)
        elif self.min_candle > op_values["rev_sell"] and self.min_candle <= op_values["buy"]:
            self.senerio2(op_values, quantity, fyers)
        elif self.min_candle > op_values["buy"] and self.min_candle <= op_values["sell"]:
            self.senerio3(op_values, quantity, fyers)
        elif self.min_candle > op_values["sell"] and self.min_candle <= op_values["rev_buy"]:
            self.senerio4(op_values, quantity, fyers)
        elif self.min_candle > op_values["rev_buy"]:
            self.senerio5(op_values, quantity, fyers)
        return 1

    def getITMCeContractName(self):
        stock_atm = int(self.atm_strikeprice) - 500
        month = self.weekly_contract_date.month
        if month < 10 :
            month_str = "0" + str(month)
        elif month == 10:
            month_str = "O"
        elif month == 11:
            month_str = "N"
        elif month == 12:
            month_str = "DEC"
        day = self.weekly_contract_date.day
        if day < 10 :
            day_str = "0" + str(day)
        else:
            day_str = str(day)
        ce_contract_name = "BANKNIFTY21" + month_str + day_str + str(stock_atm) + "CE"
        return ce_contract_name

    def getITMPeContractName(self):
        stock_atm  = int(self.atm_strikeprice) + 500
        month = self.weekly_contract_date.month
        if month < 10 :
            month_str = "0" + str(month)
        elif month == 10:
            month_str = "O"
        elif month == 11:
            month_str = "N"
        elif month == 12:
            month_str = "DEC"
        day = self.weekly_contract_date.day
        if day < 10 :
            day_str = "0" + str(day)
        else:
            day_str = str(day)
        pe_contract_name = "BANKNIFTY21" + month_str + day_str + str(stock_atm) + "PE"
        return pe_contract_name	

    def placeOptionsOrder(self, order_value, difference, side, fyers):
        if side == 1:
            contract = self.getITMCeContractName()
            options_order_value = self.atm_ce_value + (0.7*(self.atm_strikeprice - order_value))
            options_difference = 0.7*(difference)
        elif side == -1:
            contract = self.getITMPeContractName()
            options_order_value = self.atm_pe_value - (0.7*(self.atm_strikeprice - order_value))
            options_difference = 0.7*(difference)
        self.placeOrder(contract, self.no_of_lots, options_order_value, options_difference, fyers)

    def placeOrder(self, symbol, quantity, order_value, difference, fyers):
        print(symbol)
        number_of_stocks = quantity*25 #banknifty lot size is in 50 multiples. 
        stop_price = order_value - 1
        response = fyers.place_orders(
            token = self.access_token,
            data = {
                "symbol" : "NSE:" + symbol,
                "qty" : number_of_stocks,
                "type" : 4,
                "side" : 1,
                "productType" : "BO",
                "limitPrice" : order_value,
                "stopPrice" : stop_price,    
                "disclosedQty" : 0,
                "validity" : "DAY",
                "offlineOrder" : "False",
                "stopLoss" : int(difference),
                "takeProfit" : int(difference),
                }
            )
        print(response)
        return 1

    def senerio1(self, op_values, quantity, fyers):
        difference = abs(op_values["buy"] - op_values["rev_sell"])
        target = abs(op_values["rev_sell"] - difference)
        stop_loss = op_values["buy"]
        order_value = op_values["rev_sell"]
        side = -1
        self.placeOptionsOrder(order_value, difference, side, fyers)
        return 1

    def senerio2(self, op_values, quantity, fyers):
        difference = abs(op_values["buy"] - op_values["rev_sell"])
        target = abs(op_values["rev_sell"] - difference)
        stop_loss = op_values["buy"]
        order_value = op_values["rev_sell"]  
        side = -1
        self.placeOptionsOrder(order_value, difference, side, fyers)
        
        difference = abs(op_values["buy"] - op_values["rev_sell"])
        target = abs(op_values["buy"] + difference)
        stop_loss = op_values["rev_sell"]
        order_value = op_values["buy"] 
        side = 1
        self.placeOptionsOrder(order_value, difference, side, fyers)
        return 1

    def senerio3(self, op_values, quantity, fyers):
        difference = abs(op_values["buy"] - op_values["rev_sell"])
        target = abs(op_values["buy"] - difference)
        stop_loss = op_values["rev_sell"]
        order_value = op_values["buy"]  
        side = 1
        self.placeOptionsOrder(order_value, difference, side, fyers)

        difference = abs(op_values["rev_buy"] - op_values["sell"])
        target = abs(op_values["sell"] + difference)
        stop_loss =  op_values["rev_buy"]
        order_value = op_values["sell"]  
        side = -1
        self.placeOptionsOrder(order_value, difference, side, fyers)
        return 1

    def senerio4(self, op_values, quantity, fyers):
        difference = abs(op_values["rev_buy"] - op_values["sell"])
        target = abs(op_values["sell"] - difference)
        stop_loss =  op_values["rev_buy"]
        order_value = op_values["sell"]  
        side = -1
        self.placeOptionsOrder(order_value, difference, side, fyers)

        difference = abs(op_values["rev_buy"] - op_values["sell"])
        target = abs(op_values["rev_buy"] + difference)
        stop_loss =  op_values["sell"]
        order_value = op_values["rev_buy"]  
        side = 1
        self.placeOptionsOrder(order_value, difference, side, fyers)
        return 1
    
    def senerio5(self, op_values, quantity, fyers):
        difference = abs(op_values["rev_buy"] - op_values["sell"])
        target = abs(op_values["rev_buy"] + difference)
        stop_loss =  op_values["sell"]
        order_value = op_values["rev_buy"]  
        side = 1
        self.placeOptionsOrder(order_value, difference, side, fyers)
        return 1

    def run(self):
        fyers = self.generateAccess()
        op_values = self.calculateOPValues()
        self.decissionFunction(op_values, self.no_of_lots, fyers)
import math
import datetime
from datetime import timedelta
from .variables import *
from bn_options.models import BNOptionsBotOrders

class BNOptionsBot():
    def __init__(self,order_value,side,difference):
        self.order_value = order_value
        self.side = side
        self.difference = difference

    def roundup(self,x):
        x = int(x)
        return int(math.ceil(x / 100.0)) * 100

    def getOptionsContract(self,futures_value,side):
        if side==1:
            value = self.roundup(futures_value)
            value = value - OPTIONS_DEPTH
            contract = BANKNIFTY_OPTIONS_CONTRACT_YEAR_MONTH_DATE + str(value) + "CE"
        elif side == -1:
            value = self.roundup(futures_value)
            value = value + OPTIONS_DEPTH
            contract = BANKNIFTY_OPTIONS_CONTRACT_YEAR_MONTH_DATE + str(value) + "PE"
        return contract

    def getOptionsData(self,contract):
        start_date = datetime.datetime.now() - timedelta(minutes=5)
        end_date = datetime.datetime.now()
        hist_data = td_obj.get_historic_data(BN_FUTURES_CONTRACT_FETCH_VALUES,
                                             start_time=start_date ,end_time=end_date,
                                             duration='1 D',
                                             bar_size="1min")
        close_value = hist_data[::-1][0]['c']
        close_value = int(close_value)
        return close_value

    def logic(self):
        options_contract = self.getOptionsContract(self.order_value,self.side)
        premium_value = self.getOptionsData(options_contract)
        take_profit_value = int((premium_value*0.1) + premium_value)
        stoploss_value = int(premium_value - (premium_value*0.1))
        db_obj, created = BNOptionsBotOrders.objects.get_or_create(dummy_id=1)
        db_obj.order_value = premium_value
        db_obj.contract = options_contract
        db_obj.save()
        return premium_value

# write all the functions which needs to be run on celery
from datetime import timedelta
import datetime
from bn_futures.models import BNFuturesBotOrders
from truedata_ws.websocket.TD import TD
from .variables import *
from .run import executeBNOptionsOrder

td_obj = TD(USERNAME, PASSWORD)
def checkBNFuturesToExecuteOptionsTrade():
    td_obj = TD(USERNAME, PASSWORD)
    start_date = datetime.datetime.now() - timedelta(minutes=15)
    end_date = datetime.datetime.now()
    hist_data = td_obj.get_historic_data("BANKNIFTY-I",start_time=start_date ,end_time=end_date, no_of_bars=5, bar_size='1 min')
    current_market_value = hist_data[::-1][0]['c']
    td_obj.disconnect()
    db_obj, created = BNFuturesBotOrders.objects.get_or_create(dummy_id=1)
    order_value_1 = db_obj.order_value_1
    side_1 =db_obj.side_1
    order_value_2 = db_obj.order_value_2
    side_2 = db_obj.side_2
    # checking condition
    if order_value_1 == 0:
        if side_2 == 1:
            if current_market_value > order_value_2 :
                # execute
                pass
            else:
                return 0
    if order_value_2 == 0:
        if side_1 == -1:
            if current_market_value < order_value_1:
                # execute
                pass
            else:
                return 0
    if order_value_1 !=0 and order_value_2 !=0:
        if side_1 == -1:
            if current_market_value < order_value_1:
                # execute
            elif current_market_value > order_value_2:
                # execute
            else:
                return 0



def checkBNFuturesToExitOptionsTrade():
    pass
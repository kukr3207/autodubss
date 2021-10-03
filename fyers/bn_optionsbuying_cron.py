from truedata_ws.websocket.TD import TD
from .models import UserBNOptionsBuyingFyersRelation as ubofr
import multiprocessing
from .bn_optionsbuying_bot import BNOptionsBuyingBot
import datetime
from datetime import timedelta
import pytz
from fyers_api import accessToken
from fyers_api import fyersModel
import time

REALTIME_PORT = 8083
HISTORY_PORT = 8093
USERNAME = "FYERS1201"
PASSWORD = "4jV4JgKB"
HOLIDAY_LIST = ["26-01-2021", "11-03-2021", "29-03-2021", "02-04-2021", "14-04-2021", "21-04-2021", "13-05-2021", "21-07-2021", "19-08-2021", "10-09-2021" "15-10-2021", "05-11-2021", "19-11-2021", '03-01-2021', '10-01-2021', '17-01-2021', '24-01-2021', '31-01-2021', '07-02-2021', '14-02-2021', '21-02-2021', '28-02-2021', '07-03-2021', '14-03-2021', '21-03-2021', '28-03-2021', '04-04-2021', '11-04-2021', '18-04-2021', '25-04-2021', '02-05-2021', '09-05-2021', '16-05-2021', '23-05-2021', '30-05-2021', '06-06-2021', '13-06-2021', '20-06-2021', '27-06-2021', '04-07-2021', '11-07-2021', '18-07-2021', '25-07-2021', '01-08-2021', '08-08-2021', '15-08-2021', '22-08-2021', '29-08-2021', '05-09-2021', '12-09-2021', '19-09-2021', '26-09-2021', '03-10-2021', '10-10-2021', '17-10-2021', '24-10-2021', '31-10-2021', '07-11-2021', '14-11-2021', '21-11-2021', '28-11-2021', '05-12-2021', '12-12-2021', '19-12-2021', '26-12-2021', '02-01-2021', '09-01-2021', '16-01-2021', '23-01-2021', '30-01-2021', '06-02-2021', '13-02-2021', '20-02-2021', '27-02-2021', '06-03-2021', '13-03-2021', '20-03-2021', '27-03-2021', '03-04-2021', '10-04-2021', '17-04-2021', '24-04-2021', '01-05-2021', '08-05-2021', '15-05-2021', '22-05-2021', '29-05-2021', '05-06-2021', '12-06-2021', '19-06-2021', '26-06-2021', '03-07-2021', '10-07-2021', '17-07-2021', '24-07-2021', '31-07-2021', '07-08-2021', '14-08-2021', '21-08-2021', '28-08-2021', '04-09-2021', '11-09-2021', '18-09-2021', '25-09-2021', '02-10-2021', '09-10-2021', '16-10-2021', '23-10-2021', '30-10-2021', '06-11-2021', '13-11-2021', '20-11-2021', '27-11-2021', '04-12-2021', '11-12-2021', '18-12-2021', '25-12-2021']

WEEKLY_CONTRACT_DATE = datetime.datetime(2021,10,7)

def getPreviousDayValues(td_obj):
    end_date = datetime.datetime.today() - timedelta(days=1)
    hist_data = td_obj.get_historic_data("BANKNIFTY-I", end_time=end_date, duration='10 D', bar_size="EOD")
    time.sleep(0.1)
    previous_trading_date = (datetime.datetime.today() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) 
    previous_trading_date_str = datetime.datetime.strftime(previous_trading_date,"%d-%m-%Y")
    while previous_trading_date_str in HOLIDAY_LIST : 
        previous_trading_date = (previous_trading_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) 
        previous_trading_date_str = datetime.datetime.strftime(previous_trading_date,"%d-%m-%Y")
    for i in hist_data[::-1]:
        if True:
            pre_high = i["h"]
            pre_low = i["l"]
            pre_close = i["c"]
            wrong_previousday_values = 0
            break
        else:
            print("problem in previousdayvalues loop")
            wrong_previousday_values = 1
    print("Previous day high = {}, Previous day low = {}, Previous day close = {}".format(pre_high, pre_low, pre_close))
    print()
    return  pre_high, pre_low, pre_close

def getPresentDayValues(td_obj):
    barsize = '1min'
    end_date = datetime.datetime.now()
    end_date = end_date.replace(hour=9, minute=16, second=0, microsecond=0) 
    today = datetime.datetime.strftime(end_date,"%d-%m-%Y")
    min_candle = 0
    if today not in HOLIDAY_LIST:
        hist_data = td_obj.get_historic_data("BANKNIFTY-I", end_time=end_date, duration='1 D', bar_size=barsize)
        for i in hist_data:
            if i["time"] == end_date:
                min_candle = i["c"]
                break
        print("Today 9:16 min candle close value = {}".format(min_candle))
        print()
        trading_holiday = 0
        wrong_presentday_values = 0
    else:
        print("Today is Nifty holiday/ weekend. Please comeback tomorrow")
        user_order_not_placed = 1
        user_order_not_placed_reason = "Today is Trading holiday."
    return min_candle

def getATMValue(td_obj):
    timing = (datetime.datetime.now())).replace(hour=9,minute=16,second=0)
    hist_data_9_16 = td_obj.get_historic_data("BANKNIFTY-I", start_time=timing, end_time=timing)
    stock_closing_value = hist_data_9_16[0]['c']
    stock_atm = int(round(stock_closing_value/100))*100
    return stock_atm

def getATMCeContractName(atm_strikeprice):
    stock_atm = int(atm_strikeprice)
    month = WEEKLY_CONTRACT_DATE.month
    if month < 10 :
        month_str = "0" + str(month)
    else:
        month_str = str(month)
    day = WEEKLY_CONTRACT_DATE.day
    if day < 10 :
        day_str = "0" + str(day)
    else:
        day_str = str(day)
    ce_contract_name = "BANKNIFTY21" + month_str + day_str + str(stock_atm) + "CE"
    return ce_contract_name

def getATMPeContractName(atm_strikeprice):
    stock_atm  = int(atm_strikeprice)
    month = WEEKLY_CONTRACT_DATE.month
    if month < 10 :
        month_str = "0" + str(month)
    else:
        month_str = str(month)
    day = WEEKLY_CONTRACT_DATE.day
    if day < 10 :
        day_str = "0" + str(day)
    else:
        day_str = str(day)
    pe_contract_name = "BANKNIFTY21" + month_str + day_str + str(stock_atm) + "PE"
    return pe_contract_name	

def getATMCEPEValues(td_obj, atm_strikeprice):
    ce_contract_name = getATMCeContractName(atm_strikeprice)
    pe_contract_name = getATMPeContractName(atm_strikeprice)
    timing = (datetime.datetime.now()).replace(hour=9,minute=16,second=0)
    ce_9_16_hist_data = td_obj.get_historic_data(ce_contract_name, start_time=timing, end_time=timing)
    pe_9_16_hist_data = td_obj.get_historic_data(pe_contract_name, start_time=timing, end_time=timing)
    print("&&&&&&&&&&&&&&&&&&&&&&&&")
    print(ce_9_16_hist_data)
    print(pe_9_16_hist_data)
    ce_9_16_closing_value = ce_9_16_hist_data[0]['c']
    pe_9_16_closing_value = pe_9_16_hist_data[0]['c']
    return ce_9_16_closing_value, pe_9_16_closing_value

# def eachLoop(each_item):
# 	access_token = each_item['fyers_access_token']
# 	number_of_lots = each_item['number_of_lots']
# 	user = each_item['user_id_id']
# 	algo_obj = BNOptionsBuyingBot(
# 					access_token, 
# 					each_item['prev_high'], 
# 					each_item['pre_low'], 
# 					each_item['pre_close'],
# 					each_item['min_candle'],
#                     each_item['atm_strikeprice'],
#                     each_item['atm_ce_value'],
#                     each_item['atm_pe_value'],
#                     number_of_lots
# 					)
#     algo_obj.run()

def executeBNOptionsbuyingOrder():
    td_obj = TD(USERNAME, PASSWORD)
    pre_high, pre_low, pre_close = getPreviousDayValues(td_obj)
    min_candle = getPresentDayValues(td_obj)
    stock_atm = getATMValue(td_obj)
    ce_9_16_closing_value, pe_9_16_closing_value = getATMCEPEValues(td_obj, stock_atm)
    td_obj.disconnect()
    from_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')) - timedelta(days=1)).replace(hour=15,minute=30,second=0)
    to_date = (datetime.datetime.now(tz=pytz.timezone('Asia/Kolkata')))#.replace(hour=9,minute=18,second=0)
    data = ubofr.objects.filter(date_added__gte=from_date,date_added__lte=to_date).values()
    # list_data = []
    for each_record in data:
        # each_record['prev_high'] = pre_high
        # each_record['pre_low'] = pre_low
        # each_record['pre_close'] = pre_close
        # each_record['min_candle'] = min_candle
        # each_record['atm_strikeprice'] = stock_atm
        # each_record['atm_ce_value'] = ce_9_16_closing_value
        # each_record['atm_pe_value'] = pe_9_16_closing_value
        # list_data.append(each_record)

        algo_obj = BNOptionsBuyingBot(
            each_record['fyers_access_token'],
            pre_high,
            pre_low,
            pre_close,
            min_candle,
            stock_atm,
            ce_9_16_closing_value,
            pe_9_16_closing_value,
            each_record  ['number_of_lots'],
            WEEKLY_CONTRACT_DATE
        )
        algo_obj.run()


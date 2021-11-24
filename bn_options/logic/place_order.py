import os
from fyers_api import fyersModel

def placeOrder(contract, difference,quantity,order_value, side, fyers_app_id, fyers_acces_token):
    log_path = os.getcwd() 
    fyers = fyersModel.FyersModel(client_id=fyers_app_id, token=fyers_acces_token,log_path=log_path)
    number_of_stocks = quantity*25  #banknifty lot size is in 25 multiples. 
    if side > 0:
        stop_price = int(order_value) - 2
    else:
        stop_price = int(order_value) + 1
    data = {
            "symbol" : contract,
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
    response = fyers.place_order(
        data = data
        )
    print(fyers_app_id,fyers_acces_token)
    print(data)
    print(response)
    return response 

# "NSE:" + "BANKNIFTY21NOVFUT",
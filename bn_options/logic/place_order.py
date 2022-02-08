import os
from fyers_api import fyersModel
from .models import OptionsOrdersDetails

def placeOrder(contract,quantity,order_value, fyers_app_id, fyers_acces_token):
    log_path = os.getcwd() 
    fyers = fyersModel.FyersModel(client_id=fyers_app_id, token=fyers_acces_token,log_path=log_path)
    number_of_stocks = quantity*25  #banknifty lot size is in 25 multiples.
    market_order = {
        "symbol" : contract,
        "qty" : number_of_stocks,
        "type" : 2,
        "side" : 1,
        "productType" : "INTRADAY",
        "limitPrice" : int(order_value),
        "stopPrice" : 0,
        "disclosedQty" : 0,
        "validity" : "DAY",
        "offlineOrder" : "False",
        "stopLoss" : 0,
        "takeProfit" : 0,
            }
    response = fyers.place_order(
        data = market_order
        )
    print(fyers_app_id,fyers_acces_token)
    print(data)
    print(response)
    return response


def exitOrder(id, fyers_app_id, fyers_acces_token):
    log_path = os.getcwd()
    fyers = fyersModel.FyersModel(client_id=fyers_app_id, token=fyers_acces_token, log_path=log_path)
    data = {
        "id": id
    }
    response = fyers.exit_positions(data)
    return response
from truedata_ws.websocket.TD import TD
import datetime
from datetime import timedelta
from fyers_api import accessToken
from fyers_api import fyersModel


USERNAME = "FYERS1201"
PASSWORD = "4jV4JgKB"



class IntradayStraddle:

	def __init__(self, stock, access_token):
		self.stock = stock
		self.access_token = access_token
		self.weekly_contract_date = datetime.datetime(2021,9,2)
		self.optionsDataTiming = (datetime.datetime.now()).replace(hour=11,minute=10,second=0)
		# self.close_day = (datetime.datetime.now()-timedelta(days=5)).replace(hour=15,minute=00,second=0)

	def generateAccess(self):
		try:
			is_async = False #(By default False, Change to True for asnyc API calls.)
			fyers = fyersModel.FyersModel(is_async)
			self.generateaccess_exception = 0
			return fyers
		except:
			self.generateaccess_exception = 1

	def getATMValue(self, td_obj):
		hist_data_9_55 = td_obj.get_historic_data(self.stock, start_time=self.optionsDataTiming, end_time=self.optionsDataTiming)
		stock_closing_value = hist_data_9_55[0]['c']
		if self.stock == "NIFTY-I":
			stock_atm = int(round(stock_closing_value/50))*50
		elif self.stock == "BANKNIFTY-I" :
			stock_atm = int(round(stock_closing_value/100))*100
		return stock_atm

	def getCeContractName(self, stock_atm):
		if self.stock == "NIFTY-I":
			month = self.weekly_contract_date.month
			if month < 10 :
				month_str = "0" + str(month)
			else:
				month_str = str(month)
			day = self.weekly_contract_date.day
			if day < 10 :
				day_str = "0" + str(day)
			else:
				day_str = str(day)
			ce_contract_name = "NIFTY21" + month_str + day_str + str(stock_atm) + "CE"
		elif self.stock == "BANKNIFTY-I" :
			month = self.weekly_contract_date.month
			if month < 10 :
				month_str = "0" + str(month)
			else:
				month_str = str(month)
			day = self.weekly_contract_date.day
			if day < 10 :
				day_str = "0" + str(day)
			else:
				day_str = str(day)
			ce_contract_name = "BANKNIFTY21" + month_str + day_str + str(stock_atm) + "CE"
		return ce_contract_name

	def getPeContractName(self, stock_atm):
		if self.stock == "NIFTY-I":
			month = self.weekly_contract_date.month
			if month < 10 :
				month_str = "0" + str(month)
			else:
				month_str = str(month)
			day = self.weekly_contract_date.day
			if day < 10 :
				day_str = "0" + str(day)
			else:
				day_str = str(day)
			pe_contract_name = "NIFTY21" + month_str + day_str + str(stock_atm) + "PE"
		elif self.stock == "BANKNIFTY-I" :
			month = self.weekly_contract_date.month
			if month < 10 :
				month_str = "0" + str(month)
			else:
				month_str = str(month)
			day = self.weekly_contract_date.day
			if day < 10 :
				day_str = "0" + str(day)
			else:
				day_str = str(day)
			pe_contract_name = "BANKNIFTY21" + month_str + day_str + str(stock_atm) + "PE"
		return pe_contract_name	

	def getCePlaceorderContractName(self, stock_atm):
		if self.stock == "NIFTY-I":
			month = self.weekly_contract_date.month
			month_str = str(month)
			day = self.weekly_contract_date.day
			if day < 10 :
				day_str = "0" + str(day)
			else:
				day_str = str(day)
			ce_contract_name = "NIFTY21" + month_str + day_str + str(stock_atm) + "CE"
		elif self.stock == "BANKNIFTY-I" :
			month = self.weekly_contract_date.month
			month_str = str(month)
			day = self.weekly_contract_date.day
			if day < 10 :
				day_str = "0" + str(day)
			else:
				day_str = str(day)
			ce_contract_name = "BANKNIFTY21" + month_str + day_str + str(stock_atm) + "CE"
		return ce_contract_name

	def getPePlaceorderContractName(self, stock_atm):
		if self.stock == "NIFTY-I":
			month = self.weekly_contract_date.month
			month_str = str(month)
			day = self.weekly_contract_date.day
			if day < 10 :
				day_str = "0" + str(day)
			else:
				day_str = str(day)
			pe_contract_name = "NIFTY21" + month_str + day_str + str(stock_atm) + "PE"
		elif self.stock == "BANKNIFTY-I" :
			month = self.weekly_contract_date.month
			month_str = str(month)
			day = self.weekly_contract_date.day
			if day < 10 :
				day_str = "0" + str(day)
			else:
				day_str = str(day)
			pe_contract_name = "BANKNIFTY21" + month_str + day_str + str(stock_atm) + "PE"
		return pe_contract_name

	def getCeStoplossTakeprofit(self, symbol, td_obj):
		hist_data_1 = td_obj.get_historic_data(symbol,start_time=self.optionsDataTiming, end_time=self.optionsDataTiming)
		# print(hist_data_1)
		# hist_data_1 = td_obj.get_historic_data(symbol,start_time=self.close_day, end_time=self.close_day)
		print(hist_data_1)
		ce_premium_closing_value = hist_data_1[0]['c']
		ce_stop_price = int(0.4*ce_premium_closing_value)
		ce_target_price = int(0.3*ce_premium_closing_value)
		print(ce_stop_price, ce_target_price)
		return ce_stop_price, ce_target_price

	def getPeStoplossTakeprofit(self, symbol, td_obj):
		hist_data_1 = td_obj.get_historic_data(symbol,start_time=self.optionsDataTiming, end_time=self.optionsDataTiming)
		# print(hist_data_1)
		# hist_data_1 = td_obj.get_historic_data(symbol,start_time=self.close_day, end_time=self.close_day)
		print(hist_data_1)
		pe_premium_closing_value = hist_data_1[0]['c']
		pe_stop_price = int(0.4*pe_premium_closing_value)
		pe_target_price = int(0.3*pe_premium_closing_value)
		print(pe_stop_price, pe_target_price)
		return pe_stop_price, pe_target_price

	def placeOrder(self, stock, symbol, quantity, stop_loss, take_profit, fyers):
		try:
			if self.stock == "NIFTY-I":
				number_of_stocks = quantity*50  #nifty lot size is in 50 multiples. 
			elif self.stock == "BANKNIFTY-I" :
				number_of_stocks = quantity*25 #banknifty lot size is in 50 multiples. 
			response = fyers.place_orders(
			    token = self.access_token,
			    data = {
			        "symbol" : "NSE:" + symbol,
			        "qty" : number_of_stocks,
			        "type" : 2,
			        "side" : -1,
			        "productType" : "BO",
			        "limitPrice" : 0,
			        "stopPrice" : 0,    
			        "disclosedQty" : 0,
			        "validity" : "DAY",
			        "offlineOrder" : "False",
			        "stopLoss" : int(stop_loss),
			        "takeProfit" : int(take_profit),
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

	def run(self, quantity):
		fyers = self.generateAccess()
		if self.access_token:
			td_obj = TD(USERNAME, PASSWORD)
			stock_atm = self.getATMValue(td_obj)
			ce_contract_name = self.getCeContractName(stock_atm)
			pe_contract_name = self.getPeContractName(stock_atm)
			ce_contract_name_placeorder = self.getCePlaceorderContractName(stock_atm)
			pe_contract_name_placeorder = self.getPePlaceorderContractName(stock_atm)
			ce_stop_price, ce_target_price = self.getCeStoplossTakeprofit(ce_contract_name,td_obj)
			pe_stop_price, pe_target_price = self.getPeStoplossTakeprofit(pe_contract_name,td_obj)
			td_obj.disconnect()	
			print(ce_contract_name_placeorder)
			print(pe_contract_name_placeorder)
			self.placeOrder(self.stock, ce_contract_name_placeorder, quantity, ce_stop_price, ce_target_price, fyers)
			self.placeOrder(self.stock, pe_contract_name_placeorder, quantity, pe_stop_price, pe_target_price, fyers)
				
		else:
			print("Problem in access token")
			return 0


# stock = "BANKNIFTY-I"
# access_token = "gAAAAABhLPx18HFJ_JyBMuAqcw4UjQ0e_gOT-ybl2JcRmJ4YCDZRXJ4Km1htf7hq-V6t-fYdirro5jEs-sCmUDpooYZ_zR0kqk-QJHIJjOmcMxsCjSiPKJI="
# weekly_contract_date = datetime.datetime(2021,9,2)
# obj = IntradayStraddle(stock,access_token,weekly_contract_date)
# obj.run(1)



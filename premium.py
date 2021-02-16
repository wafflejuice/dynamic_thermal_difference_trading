from exchange import Upbit, Binance, Futures
import currency

class Kimp:
	
	'''
	|	stage	|	0	|	1	|	2	|	3	|	4	|	5	|	6	|
	+-------------------+-------+-------+-------+-------+-------+-------+
	|	bound	|	-6%	|	-4%	|	-2%	|	0%	|	2%	|	4%	|	6%	|
	'''
	
	bound = [-0.06, -0.04, -0.02, 0.0, +0.02, +0.04, +0.06]
	
	@staticmethod
	def calculate_kimp(upbit, binance, coin_symbol):
		upbit_coin_price_krw = Upbit.fetch_coin_price(upbit, coin_symbol)
		binance_coin_price_krw = Binance.fetch_coin_price(binance, coin_symbol) * currency.fetch_usd_krw_currency()
		
		return (upbit_coin_price_krw - binance_coin_price_krw) / binance_coin_price_krw
	
	@classmethod
	def calculate_kimps(cls, upbit, binance, coin_symbols, reverse):
		coin_upbit_ids = []
		coin_binance_ids = []
		
		for coin_symbol in coin_symbols:
			coin_upbit_ids.append(Upbit.get_coin_id(coin_symbol))
			coin_binance_ids.append(Binance.get_coin_id(coin_symbol))
		
		upbit_tickers = upbit.fetch_tickers()
		binance_tickers = binance.fetch_tickers()
		
		coin_kimps = {}
		usd_krw_currency = currency.fetch_usd_krw_currency()
		
		for i in range(len(coin_upbit_ids)):
			if coin_upbit_ids[i] in upbit_tickers.keys() and coin_binance_ids[i] in binance_tickers.keys():
				upbit_coin_price_krw = upbit_tickers[coin_upbit_ids[i]]['last']
				binance_coin_price_usdt = binance_tickers[coin_binance_ids[i]]['last']
				binance_coin_price_krw = binance_coin_price_usdt * usd_krw_currency
				
				coin_kimps[coin_symbols[i]] = (upbit_coin_price_krw - binance_coin_price_krw) / binance_coin_price_krw
				
		return {k: v for k, v in sorted(coin_kimps.items(), key=lambda item: item[1], reverse=reverse)}

	@staticmethod
	def calculate_transfer_balance_ratio(previous_stage, current_stage):
		if previous_stage < current_stage:
			return (current_stage - previous_stage) / (6 - previous_stage)
		elif previous_stage == current_stage:
			return 0.0
		else:
			return (current_stage - previous_stage) / previous_stage
	
	@classmethod
	def calculate_stage(cls, previous_stage, current_kimp):
		if cls.bound[previous_stage] < current_kimp:
			if previous_stage == len(cls.bound) - 1:
				return previous_stage
			
			while True:
				if cls.bound[previous_stage] <= current_kimp:
					previous_stage += 1
				else:
					return previous_stage - 1
				
		elif cls.bound[previous_stage] == current_kimp:
			return previous_stage
		
		else:
			if previous_stage == 0:
				return previous_stage
			
			while True:
				if cls.bound[previous_stage] >= current_kimp:
					previous_stage -= 1
				else:
					return previous_stage + 1
	
	@classmethod
	def is_above(cls, kimp):
		if kimp < cls.bound[0]:
			return -1
		
		if cls.bound[len(cls.bound) - 1] < kimp:
			return len(cls.bound) - 1
		
		previous_stage = 0
		
		while True:
			if cls.bound[previous_stage] < kimp:
				previous_stage += 1
			else:
				return previous_stage - 1
			
	@classmethod
	def is_under(cls, kimp):
		if cls.bound[len(cls.bound) - 1] < kimp:
			return -1
		
		if kimp < cls.bound[0]:
			return 0
		
		previous_stage = len(cls.bound) - 1
		
		while True:
			if kimp < cls.bound[previous_stage]:
				previous_stage -= 1
			else:
				return previous_stage + 1


class Futp:
	@staticmethod
	def calculate_futp(binance, futures, coin_symbol):
		binance_coin_price = Binance.fetch_coin_price(binance, coin_symbol)
		futures_coin_price = Futures.fetch_coin_price(futures, coin_symbol)
		
		return (futures_coin_price - binance_coin_price) / binance_coin_price
	
	@classmethod
	def is_acceptable(cls, binance, futures, coin_symbol, gap_ratio):
		futp = cls.calculate_futp(binance, futures, coin_symbol)
		
		print(coin_symbol + ", "+str(futp)+"%")
		
		return abs(futp) < gap_ratio

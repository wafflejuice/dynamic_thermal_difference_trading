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
	def calculate_premium(coin_symbol, from_ex, to_ex, from_currency='krw', to_currency='krw'):
		usd_krw_price = currency.fetch_usd_krw_price()
		
		from_ex_price_krw = from_ex.fetch_coin_price(from_ex, coin_symbol)
		to_ex_price_krw = to_ex.fetch_coin_price(to_ex, coin_symbol) * currency.fetch_usd_krw_price()
		
		if from_currency == 'krw':
			pass
		elif from_currency == 'usd':
			from_ex_price_krw *= usd_krw_price
		
		if to_currency == 'krw':
			pass
		elif to_currency == 'usd':
			to_ex_price_krw *= usd_krw_price
		
		return (to_ex_price_krw - from_ex_price_krw) / from_ex_price_krw
	
	@classmethod
	def calculate_premiums(cls, coin_symbols, from_ex, to_ex, from_currency='krw', to_currency='krw'):
		usd_krw_price = currency.fetch_usd_krw_price()
		
		from_ex_coin_ids = []
		to_ex_coin_ids = []
		
		for coin_symbol in coin_symbols:
			from_ex_coin_ids.append(Upbit.get_coin_id(coin_symbol))
			to_ex_coin_ids.append(Binance.get_coin_id(coin_symbol))
		
		from_ex_tickers = from_ex.fetch_tickers()
		to_ex_tickers = to_ex.fetch_tickers()
		
		coin_premiums = {}
		
		for i in range(len(from_ex_coin_ids)):
			if from_ex_coin_ids[i] in from_ex_tickers.keys() and to_ex_coin_ids[i] in to_ex_tickers.keys():
				from_ex_price_krw = from_ex_tickers[from_ex_coin_ids[i]]['last']
				to_ex_price_krw = to_ex_tickers[to_ex_coin_ids[i]]['last']
				
				if from_currency == 'krw':
					pass
				elif from_currency == 'usd':
					from_ex_price_krw *= usd_krw_price
				
				if to_currency == 'krw':
					pass
				elif to_currency == 'usd':
					to_ex_price_krw *= usd_krw_price
				
				coin_premiums[coin_symbols[i]] = (to_ex_price_krw - from_ex_price_krw) / from_ex_price_krw
				
		return {k: v for k, v in sorted(coin_premiums.items(), key=lambda item: item[1])}

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
		
		return abs(futp) < gap_ratio

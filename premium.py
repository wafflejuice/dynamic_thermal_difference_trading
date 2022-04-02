from exchange.binance import Binance, Futures
import currency

class Premium:
	
	'''
	|	stage	|	0	|	1	|	2	|	3	|	4	|	5	|	6	|
	+-------------------+-------+-------+-------+-------+-------+-------+
	|	bound	|	-6%	|	-4%	|	-2%	|	0%	|	2%	|	4%	|	6%	|
	'''
	
	bound = [-0.06, -0.04, -0.02, 0.0, +0.02, +0.04, +0.06]
	
	@staticmethod
	def fetch_premium(symbol, from_market, from_ex, to_market, to_ex, from_to_rate):
		from_price = from_ex.fetch_coin_price(symbol, from_market)
		to_price = to_ex.fetch_coin_price(symbol, to_market)
		
		from_price *= from_to_rate
	
		return (to_price - from_price) / from_price
	
	@staticmethod
	def calculate_premium(symbol, from_prices, to_prices, from_to_rate):
		if symbol in from_prices.keys() and symbol in to_prices.keys():
			from_price = from_prices[symbol]
			to_price = to_prices[symbol]
		
			from_price *= from_to_rate
		
			return (to_price - from_price) / from_price
		
		return None
		
	@staticmethod
	def fetch_premiums(from_market, from_ex, to_market, to_ex):
		from_prices = from_ex.fetch_prices(from_market)
		to_prices = to_ex.fetch_prices(to_market)
		
		intersection_symbols = list(filter(lambda x: x in to_prices.keys(), from_prices.keys()))

		usd_krw_rate = currency.fetch_usd_krw_rate()
		from_to_rate = usd_krw_rate if from_market=='USDT' and to_market=='KRW' else 1 / usd_krw_rate
		
		premiums = {}
		for s in intersection_symbols:
			premiums[s] = Premium.calculate_premium(s, from_prices, to_prices, from_to_rate)
			
		return premiums
	
	@staticmethod
	def calculate_expected_profit(lot_size, from_price, to_price, withdraw_fee, from_to_rate):
		from_price *= from_to_rate
		withdraw_fee *= from_price
		
		return lot_size * (to_price - from_price) - withdraw_fee
	
	@staticmethod
	def fetch_expected_profits(lot_size, from_market, from_ex, from_addresses, to_market, to_ex, to_addresses):
		from_prices = from_ex.fetch_prices(from_market)
		to_prices = to_ex.fetch_prices(to_market)
		
		# print('from')
		# print(from_prices)
		# print('to')
		# print(to_prices)
		
		withdraw_fees = from_ex.fetch_withdraw_fees()
		
		intersection_symbols = list(filter(lambda x: x in to_prices.keys(), from_prices.keys()))
		# print('intersection')
		# print(intersection_symbols)
		
		intersection_networks = dict()
		for s in intersection_symbols:
			if s in from_addresses.keys() and s in to_addresses.keys():
				intersection_networks[s] = []
				for n in from_addresses[s].keys():
					if n in to_addresses[s].keys():
						intersection_networks[s].append(n)
				if not intersection_networks[s]:
					del(intersection_networks[s])
		# {'BTC':['BTC'], ...}

		usd_krw_rate = currency.fetch_usd_krw_rate()
		from_to_rate = usd_krw_rate if from_market=='USDT' and to_market=='KRW' else 1 / usd_krw_rate
		
		max_symbol = None
		max_network = None
		expected_profits = dict()
		for symbol in intersection_networks.keys():
			max_expected_profit_per_chain = 0
			for network in intersection_networks[symbol]:
				expected_profit_per_chain = Premium.calculate_expected_profit(lot_size, from_prices[symbol], to_prices[symbol], withdraw_fees[symbol][network], from_to_rate)
				if expected_profit_per_chain > max_expected_profit_per_chain:
					max_symbol = symbol
					max_network = network
			
		return expected_profits
	
	@staticmethod
	def fetch_max_expected_profit(lot_size, from_market, from_ex, from_addresses, to_market, to_ex, to_addresses):
		from_prices = from_ex.fetch_prices(from_market)
		to_prices = to_ex.fetch_prices(to_market)
		
		withdraw_fees = from_ex.fetch_withdraw_fees(from_addresses)
		
		intersection_networks = dict()
		for s in from_addresses.keys():
			if s in from_addresses.keys() and s in to_addresses.keys():
				intersection_networks[s] = []
				for n in from_addresses[s].keys():
					if n in to_addresses[s].keys():
						intersection_networks[s].append(n)
				if not intersection_networks[s]:
					del (intersection_networks[s])
		# {'BTC':['BTC'], ...}
		# print(withdraw_fees)
		# print(intersection_networks)
		
		usd_krw_rate = currency.fetch_usd_krw_rate()
		from_to_rate = usd_krw_rate if from_market == 'USDT' and to_market == 'KRW' else 1 / usd_krw_rate
		
		max_expected_profit = 0
		max_symbol = None
		max_network = None
		for symbol in intersection_networks.keys():
			for network in intersection_networks[symbol]:
				# print(f'symbol={symbol}, network={network}')
				expected_profit_per_chain = Premium.calculate_expected_profit(lot_size, from_prices[symbol], to_prices[symbol],
																			  withdraw_fees[symbol][network],
																			  from_to_rate)
				if expected_profit_per_chain > max_expected_profit:
					max_expected_profit = expected_profit_per_chain
					max_symbol = symbol
					max_network = network
		
		return max_symbol, max_network, max_expected_profit
	
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

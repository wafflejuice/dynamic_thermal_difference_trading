from exchange.binance import Binance, Futures
import currency

class Premium:
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
		
		withdraw_fees = from_ex.fetch_withdraw_fees()
		
		intersection_symbols = list(filter(lambda x: x in to_prices.keys(), from_prices.keys()))

		# {'BTC':['BTC'], ...}
		intersection_networks = dict()
		for s in intersection_symbols:
			if s in from_addresses.keys() and s in to_addresses.keys():
				intersection_networks[s] = []
				for n in from_addresses[s].keys():
					if n in to_addresses[s].keys():
						intersection_networks[s].append(n)
				if not intersection_networks[s]:
					del(intersection_networks[s])

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

		# {'BTC':['BTC'], ...}
		intersection_networks = dict()
		for s in from_addresses.keys():
			if s in from_addresses.keys() and s in to_addresses.keys():
				intersection_networks[s] = []
				for n in from_addresses[s].keys():
					if n in to_addresses[s].keys():
						intersection_networks[s].append(n)
				if not intersection_networks[s]:
					del (intersection_networks[s])
		
		usd_krw_rate = currency.fetch_usd_krw_rate()
		from_to_rate = usd_krw_rate if from_market == 'USDT' and to_market == 'KRW' else 1 / usd_krw_rate
		
		max_expected_profit = 0
		max_symbol = None
		max_network = None
		for symbol in intersection_networks.keys():
			for network in intersection_networks[symbol]:
				expected_profit_per_chain = Premium.calculate_expected_profit(lot_size, from_prices[symbol], to_prices[symbol],
																			  withdraw_fees[symbol][network],
																			  from_to_rate)
				if expected_profit_per_chain > max_expected_profit:
					max_expected_profit = expected_profit_per_chain
					max_symbol = symbol
					max_network = network
		
		return max_symbol, max_network, max_expected_profit

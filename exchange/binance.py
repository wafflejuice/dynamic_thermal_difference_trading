from exchange.base_exchange import BaseExchange
from binance.spot import Spot
import time


class Binance(BaseExchange):
	TAKER_FEE = 0.001
	
	def __init__(self, api_key, secret_key):
		self._api_key = api_key
		self._secret_key = secret_key

		self._client = Spot(key=api_key, secret=secret_key)
		
	
	def to_market_code(self, symbol, market):
		return symbol+market
	
	def to_symbol(self, market_code, market):
		return market_code[:-len(market)]
	
	def to_market(self, market_code, symbol):
		pass
	
	def fetch_server_timestamp(self):
		return int(self._client.time()['serverTime'])
	
	def fetch_symbols(self):
		pass
	
	def fetch_market_codes(self):
		pass
	
	def fetch_price(self, symbol, market):
		market_code = self.to_market_code(symbol, market)
		return float(self._client.ticker_price(market_code)['price'])
	
	def fetch_prices(self, market):
		tickers = self._client.ticker_price()
		
		prices = {}
		for ticker in tickers:
			prices[self.to_symbol(ticker['symbol'], market)] = float(ticker['price'])
		
		return prices
	
	def fetch_balance(self, symbol):
		all_coins_info = self._client.coin_info()
		
		for coin_info in all_coins_info:
			if coin_info['coin'] == symbol:
				return float(coin_info['free'])
		
		return None
	
	def is_wallet_withdrawable(self, symbol, network):
		all_coins_info = self._client.coin_info()
		print(all_coins_info)
		for coin_info in all_coins_info:
			if coin_info['coin'] == symbol:
				print(coin_info)
				for network_info in coin_info['networkList']:
					if network_info['network'] == network:
						return network_info['withdrawEnable']
		return False
	
	def is_wallet_depositable(self, symbol, network):
		all_coins_info = self._client.coin_info()
		
		for coin_info in all_coins_info:
			if coin_info['coin'] == symbol:
				for network_info in coin_info['networkList']:
					if network_info['network'] == network:
						return network_info['depositEnable']
		return False
	
	def fetch_withdraw_fee(self, symbol, network):
		all_coins_info = self._client.coin_info()
		
		for coin_info in all_coins_info:
			if coin_info['coin'] == symbol:
				for network_info in coin_info['networkList']:
					if network_info['network'] == network:
						return network_info['withdrawFee']
		return False
	
	def fetch_withdraw_fees(self, addresses=None):
		all_coins_info = self._client.coin_info()
		
		withdraw_fees = dict()
		for coin_info in all_coins_info:
			withdraw_fees[coin_info['coin']] = dict()
			for network in coin_info['networkList']:
				withdraw_fees[coin_info['coin']][network['network']] = float(network['withdrawFee'])
		
		return withdraw_fees
	
	def withdraw(self, symbol, to_addr, to_tag, amount, network=None):
		return self._client.withdraw(symbol, amount, to_addr, addressTag=to_tag, network=network)
	
	def wait_withdraw(self, id_):
		withdraw_history = self._client.withdraw_history()
		
		start_time_s = time.time()
		term_s = 1
		
		while True:
			if time.time() - start_time_s < term_s:
				continue
			
			for withdraw in withdraw_history:
				if withdraw['id'] == id_:
					# 0:Email Sent, 1:Cancelled, 2:Awaiting Approval, 3:Rejected, 4:Processing, 5:Failure, 6:Completed
					if withdraw['status'] == 6:
						return True
					elif withdraw['status'] in [1, 3, 5]:
						return False
					break
			
			withdraw_history = self._client.withdraw_history()
			start_time_s = time.time()
		
		return False
	
	def fetch_txid(self, id_):
		withdraw_history = self._client.withdraw_history()
		
		start_time_s = time.time()
		term_s = 1
		
		while True:
			if time.time() - start_time_s < term_s:
				continue
			
			for withdraw in withdraw_history:
				if withdraw['id'] == id_:
					if withdraw['txid'] is not None:
						return withdraw['txid']
					break
			
			withdraw_history = self._client.withdraw_history()
			start_time_s = time.time()
		
		return None
	
	def wait_deposit(self, txid):
		deposit_history = self._client.deposit_history()
		
		start_time_s = time.time()
		term_s = 1
		
		while True:
			if time.time() - start_time_s < term_s:
				continue
			
			for deposit in deposit_history:
				if deposit['txId'].lower() == txid.lower():
					# 0:pending, 6:credited but cannot withdraw, 1:success
					if deposit['status'] in [1, 6]:
						return True
					break
			
			deposit_history = self._client.deposit_history()
			start_time_s = time.time()
		
		return None

	def fetch_deposit_amount(self, txid):
		deposit_history = self._client.deposit_history()
		
		for deposit in deposit_history:
			if deposit['txId'].lower() == txid.lower():
				return float(deposit['amount'])
		
		return None
		
	def create_market_buy_order(self, symbol, market, price):
		price = self.price_filter(symbol, market, price)
		order = self._client.new_order(self.to_market_code(symbol, market), 'BUY', 'MARKET', quoteOrderQty=price)
		
		return order['clientOrderId']
	
	def create_market_sell_order(self, symbol, market, volume):
		volume = self.quantity_filter(symbol, market, volume, True)
		order = self._client.new_order(self.to_market_code(symbol, market), 'SELL', 'MARKET', quantity=volume)
		
		return order['clientOrderId']

	def order_executed_volume(self, symbol, market, id_):
		order = self._client.get_order(self.to_market_code(symbol, market), origClientOrderId=id_)
		executed_volume = float(order['executedQty'])
		
		return executed_volume

	def is_order_fully_executed(self, symbol, market, id_):
		order = self._client.get_order(self.to_market_code(symbol, market), origClientOrderId=id_)
		# ACTIVE, CANCELLED, FILLED
		if order['status'] == 'FILLED':
			return True
		
		return False
	
	def wait_order(self, symbol, market, id_):
		order = self._client.get_order(self.to_market_code(symbol, market), origClientOrderId=id_)
		
		start_time_s = time.time()
		term_s = 1
		
		while True:
			if time.time() - start_time_s < term_s:
				continue
				
			if order['status'] == 'FILLED':
				return True
			elif order['status'] == 'CANCELLED':
				return False
			
			order = self._client.get_order(symbol, market, origClientOrderId=id_)
			start_time_s = time.time()
		
		return False
	
	def cancel_order(self, symbol, market, id_):
		self._client.cancel_order(self.to_market_code(symbol, market), origClientOrderId=id_)
		
	def fetch_filters(self, symbol, market):
		exchange_info = self._client.exchange_info(self.to_market_code(symbol, market))
		filters = exchange_info['symbols'][0]['filters']
		
		casted_filters = {}
		for filter_ in filters:
			if filter_['filterType'] == 'PRICE_FILTER':
				min_price = float(filter_['minPrice'])
				max_price = float(filter_['maxPrice'])
				tick_size = float(filter_['tickSize'])
				casted_filters['price_filter'] = (min_price, max_price, tick_size)
			elif filter_['filterType'] == 'LOT_SIZE':
				min_qty = float(filter_['minQty'])
				max_qty = float(filter_['maxQty'])
				step_size = float(filter_['stepSize'])
				casted_filters['lot_size'] = (min_qty, max_qty, step_size)
			elif filter_['filterType'] == 'MARKET_LOT_SIZE':
				min_qty = float(filter_['minQty'])
				max_qty = float(filter_['maxQty'])
				step_size = float(filter_['stepSize'])
				casted_filters['market_lot_size'] = (min_qty, max_qty, step_size)
		
		return casted_filters

	def price_filter(self, symbol, market, price):
		filters = self.fetch_filters(symbol, market)
		
		if 'price_filter' in filters.keys():
			min_price = filters['price_filter'][0]
			max_price = filters['price_filter'][1]
			tick_size = filters['price_filter'][2]
			
			price = max(min_price, price)
			price = min(price, max_price)
			if tick_size > 0.0:
				price = int(price / tick_size) * tick_size
		
		return price
	
	def quantity_filter(self, symbol, market, quantity, is_market=False):
		filters = self.fetch_filters(symbol, market)
		
		# LOT_SIZE
		if 'lot_size' in filters.keys():
			min_qty = filters['lot_size'][0]
			max_qty = filters['lot_size'][1]
			step_size = filters['lot_size'][2]
			
			quantity = max(min_qty, quantity)
			quantity = min(quantity, max_qty)
			if step_size > 0.0:
				quantity = int(quantity / step_size) * step_size

		# MARKET_LOT_SIZE
		# market order should be use both LOT_SIZE, MARKET_LOT_SIZE filter
		if is_market and 'market_lot_size' in filters.keys():
			min_qty = filters['market_lot_size'][0]
			max_qty = filters['market_lot_size'][1]
			step_size = filters['market_lot_size'][2]
			
			quantity = max(min_qty, quantity)
			quantity = min(quantity, max_qty)
			if step_size > 0.0:
				quantity = int(quantity / step_size) * step_size
		
		return quantity

class Futures(BaseExchange):
	TAKER_FEE = 0.0004
	
	@classmethod
	def get_coin_id(cls, coin_symbol):
		return coin_symbol + cls.USDT_SYMBOL
		
	@staticmethod
	def fetch_server_time(futures):
		return futures.fetch_time()
	
	@staticmethod
	def fetch_coin_symbols(futures):
		futures_markets = futures.fetch_markets()
		futures_symbols = []
		
		for market in futures_markets:
			if market['quote'] == 'USDT':
				futures_symbols.append(market['base'])
		
		return futures_symbols
	
	@classmethod
	def fetch_balance(cls, futures):
		return futures.fetch_balance()['USDT']['free']
	
	# + : Long, - : Short
	@classmethod
	def fetch_coin_count(cls, futures, coin_symbol):
		futures_positions = futures.fetch_positions()
		futures_coin_positions = list(
			filter(lambda x: x['symbol'] == cls.get_coin_id(coin_symbol), futures_positions))
		futures_coin_position = float(futures_coin_positions[0]['positionAmt'])
		
		return futures_coin_position
	
	@classmethod
	def fetch_coin_price(cls, futures, coin_symbol):
		futures_coin_ticker = futures.fapiPublicGetTickerPrice({
			'symbol': cls.get_coin_id(coin_symbol)
		})
		futures_coin_price = float(futures_coin_ticker['price'])
		
		return futures_coin_price
	
	@classmethod
	def fetch_market_restricts(cls, futures, coin_symbol):
		futures.load_markets()
		market = futures.markets[coin_symbol+'/USDT']
		
		return market
	
	@classmethod
	def fetch_coin_price_precision(cls, futures, coin_symbol):
		restricts = cls.fetch_market_restricts(futures, coin_symbol)
		price_precision = restricts['precision']['price']
		
		return price_precision
	
	@classmethod
	def fetch_coin_amount_precision(cls, futures, coin_symbol):
		restricts = cls.fetch_market_restricts(futures, coin_symbol)
		quantity_precision = restricts['precision']['amount']
		
		return quantity_precision
	
	@classmethod
	def adjust_leverage(cls, futures, coin_symbol, leverage):
		if leverage < 1:
			raise ValueError("leverage should be at least x1")
		
		futures.fapiPrivatePostLeverage({
			'symbol': cls.get_coin_id(coin_symbol),
			'leverage': leverage,
		})
		
	# coin_count is right. not usdt.
	@classmethod
	def market_order(cls, futures, coin_symbol, coin_count, side, reduce_only):
		if reduce_only:
			futures.fapiPrivatePostOrder({
				'symbol': cls.get_coin_id(coin_symbol),
				'side': side,
				'type': 'MARKET',
				'quantity': coin_count,
				'reduceOnly': 'true',
			})
		else:
			futures.fapiPrivatePostOrder({
				'symbol': cls.get_coin_id(coin_symbol),
				'side': side,
				'type': 'MARKET',
				'quantity': coin_count,
			})
			
	@classmethod
	def market_long(cls, futures, coin_symbol, coin_count, reduce_only):
		cls.market_order(futures, coin_symbol, coin_count, 'BUY', reduce_only)
		
	@classmethod
	def market_short(cls, futures, coin_symbol, coin_count, reduce_only):
		cls.market_order(futures, coin_symbol, coin_count, 'SELL', reduce_only)
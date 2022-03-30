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
	
	def to_symbol(self, market_code):
		pass
	
	def fetch_server_timestamp(self):
		return int(self._client.time()['serverTime'])
	
	def fetch_symbols(self):
		# return self._client.ticker_price()
		pass
	
	def fetch_price(self, symbol, market):
		market_code = self.to_market_code(symbol, market)
		return float(self._client.ticker_price(market_code)['price'])
	
	def fetch_balance(self, symbol):
		all_coins_info = self._client.coin_info()
		
		# print(all_coins_info)
		
		for coin_info in all_coins_info:
			if coin_info['coin'] == symbol:
				return coin_info['free']
		
		return None
	
	def is_wallet_withdrawable(self, symbol, network):
		all_coins_info = self._client.coin_info()
		
		for coin_info in all_coins_info:
			if coin_info['coin'] == symbol:
				for network_info in coin_info['networkList']:
					if network_info['network'] == network:
						return network_info['withdrawEnable']
					print('Such network is not supported for the symbol')
					return False
			print('Such symbol does not exist')
			return False
		return False
	
	def is_wallet_depositable(self, symbol, network):
		all_coins_info = self._client.coin_info()
		
		for coin_info in all_coins_info:
			if coin_info['coin'] == symbol:
				for network_info in coin_info['networkList']:
					if network_info['network'] == network:
						return network_info['depositEnable']
					print('Such network is not supported for the symbol')
					return False
			print('Such symbol does not exist')
			return False
		return False
	
	def fetch_withdraw_fee(self, symbol, network):
		all_coins_info = self._client.coin_info()
		
		for coin_info in all_coins_info:
			if coin_info['coin'] == symbol:
				for network_info in coin_info['networkList']:
					if network_info['network'] == network:
						return network_info['withdrawFee']
					print('Such network is not supported for the symbol')
					return False
			print('Such symbol does not exist')
			return False
		return False
	
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
		
	def create_market_buy_order(self, symbol, market, price):
		order = self._client.new_order(self.to_market_code(symbol, market), 'BUY', 'MARKET', quoteOrderQty=price)
		
		return order['clientOrderId']
	
	def create_market_sell_order(self, symbol, market, volume):
		volume = self.quantity_filter(volume, True)
		order = self._client.new_order(self.to_market_code(symbol, market), 'SELL', 'MARKET', quantity=volume)
		
		return order['clientOrderId']

	def order_executed_volume(self, symbol, id_):
		order = self._client.get_order(symbol, origClientOrderId=id_)
		executed_volume = float(order['executedQty'])
		
		return executed_volume

	def is_order_fully_executed(self, symbol, id_):
		order = self._client.get_order(symbol, origClientOrderId=id_)
		# ACTIVE, CANCELLED, FILLED
		if order['status'] == 'FILLED':
			return True
		
		return False
	
	def wait_order(self, symbol, id_):
		order = self._client.get_order(symbol, origClientOrderId=id_)
		
		start_time_s = time.time()
		term_s = 1
		
		while True:
			if time.time() - start_time_s < term_s:
				continue
				
			if order['status'] == 'FILLED':
				return True
			elif order['status'] == 'CANCELLED':
				return False
			
			order = self._client.get_order(symbol, origClientOrderId=id_)
			start_time_s = time.time()
		
		return False
	
	def cancel_order(self, symbol, id_):
		self._client.cancel_order(symbol, origClientOrderId=id_)

	def price_filter(self, price):
		min_price = 0.00000100
		max_price = 100000.00000000
		tick_size = 0.00000100
		
		price = max(min_price, price)
		price = min(price, max_price)
		price = int(price / tick_size) * tick_size
		# price = '{:.6f}'.format(price)
		
		return price
	
	def quantity_filter(self, quantity, is_market=False):
		# MARKET_LOT_SIZE
		if is_market:
			minQty = 0.00100000
			maxQty = 100000.00000000
			step_size = 0.00100000
		
			quantity = max(minQty, quantity)
			quantity = min(quantity, maxQty)
			quantity = int(quantity / step_size) * step_size
			# quantity = '{:.3f}'.format(quantity)
		# LOT_SIZE
		else:
			minQty = 0.00100000
			maxQty = 100000.00000000
			step_size = 0.00100000
			
			quantity = max(minQty, quantity)
			quantity = min(quantity, maxQty)
			quantity = int(quantity / step_size) * step_size
			# quantity = '{:.3f}'.format(quantity)
		
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
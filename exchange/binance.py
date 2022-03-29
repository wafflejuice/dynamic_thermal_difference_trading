from exchange.base_exchange import BaseExchange
from binance.spot import Spot


class Binance(BaseExchange):
	TAKER_FEE = 0.001
	
	def __init__(self, api_key, secret_key):
		self._api_key = api_key
		self._secret_key = secret_key

		self._client = Spot(key=api_key, secret=secret_key)
		
	
	def to_market_code(self, symbol, market):
		pass
	
	def to_symbol(self, market_code):
		pass
	
	def fetch_server_timestamp(self):
		return self.time()
	
	def fetch_symbols(self):
		pass
	
	def fetch_price(self, symbol, market):
		pass
	
	def fetch_balance(self, symbol):
		pass
	
	def is_wallet_withdrawable(self, symbol, amount=0.0):
		pass
	
	def is_wallet_depositable(self, symbol):
		pass
	
	def fetch_withdraw_fee(self, symbol):
		pass
	
	def withdraw(self, symbol, to_addr, to_tag, amount, chain=None):
		pass
	
	def wait_withdraw(self, uuid):
		pass
	
	def fetch_txid(self, uuid):
		pass
	
	def wait_deposit(self, txid):
		pass
	
	def create_market_buy_order(self, symbol, market, price):
		pass
	
	def create_market_sell_order(self, symbol, market, volume):
		pass


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
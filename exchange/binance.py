from exchange.base_exchange import BaseExchange


class Binance(BaseExchange):
	TAKER_FEE = 0.001
	
	
	@classmethod
	def get_coin_id(cls, coin_symbol):
		return coin_symbol + '/' + cls.USDT_SYMBOL
	
	@staticmethod
	def fetch_server_time(binance):
		return binance.fetch_time()
	
	@staticmethod
	def fetch_market_symbols(binance):
		binance_markets = binance.fetch_markets()
		binance_symbols = []
		
		for market in binance_markets:
			if market['quote'] == 'USDT':
				binance_symbols.append(market['base'])
		
		return binance_symbols
	
	@classmethod
	def fetch_balance(cls, binance):
		return binance.fetch_balance()[cls.USDT_SYMBOL]['free']
	
	@staticmethod
	def fetch_coin_count(binance, coin_symbol):
		return binance.fetch_balance()[coin_symbol]['free']

	@classmethod
	def fetch_coin_price(cls, binance, coin_symbol):
		return binance.fetch_ticker(cls.get_coin_id(coin_symbol))['last']
	
	@classmethod
	def fetch_market_restricts(cls, binance, coin_symbol):
		binance.load_markets()
		market = binance.markets[cls.get_coin_id(coin_symbol)]
		
		return market
	
	@classmethod
	def fetch_coin_price_precision(cls, binance, coin_symbol):
		restricts = cls.fetch_market_restricts(binance, coin_symbol)
		price_precision = restricts['precision']['price']
		
		return price_precision
	
	@classmethod
	def fetch_coin_amount_precision(cls, binance, coin_symbol):
		restricts = cls.fetch_market_restricts(binance, coin_symbol)
		quantity_precision = restricts['precision']['amount']
		
		return quantity_precision
	
	@classmethod
	def is_wallet_limitless(cls, binance, coin_symbol):
		configs = binance.sapi_get_capital_config_getall()
		
		for config in configs:
			if config['coin'] == coin_symbol:
				return config['depositAllEnable'] and config['withdrawAllEnable'] and config['trading']
		
		return None
	
	@classmethod
	def fetch_coin_withdraw_fee(cls, binance, coin_symbol):
		return binance.fetch_funding_fees()['withdraw'][coin_symbol]
	
	@classmethod
	def create_market_buy_order(cls, binance, coin_symbol, coin_count):
		binance.create_market_buy_order(cls.get_coin_id(coin_symbol), coin_count)  # , {'test':True,})
		
	@classmethod
	def create_market_sell_order(cls, binance, coin_symbol, coin_count):
		binance.create_market_sell_order(cls.get_coin_id(coin_symbol), coin_count)  # , {'test':True,})
class Futures(BaseExchange):
	TAKER_FEE = 0.0004
	
	@classmethod
	def get_coin_id(cls, coin_symbol):
		return coin_symbol + cls.USDT_SYMBOL
		
	@staticmethod
	def fetch_server_time(futures):
		return futures.fetch_time()
	
	@staticmethod
	def fetch_market_symbols(futures):
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
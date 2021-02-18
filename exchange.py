import abc
import math

from telegram import Telegram


class Exchange:
	__metaclass__ = abc.ABCMeta
	
	KRW_SYMBOL = 'KRW'
	USDT_SYMBOL = 'USDT'
	
	EPOCH_TIME_TWO_HOUR_MS = 7200000

	@classmethod
	@abc.abstractmethod
	def get_coin_id(cls, coin_symbol):
		pass

	@staticmethod
	@abc.abstractmethod
	def fetch_server_time(exchange):
		pass

	@classmethod
	@abc.abstractmethod
	def fetch_balance(cls, exchange):
		pass

	@staticmethod
	@abc.abstractmethod
	def fetch_coin_count(exchange, coin_symbol):
		pass

	@staticmethod
	def telegram_me_balance(upbit, binance, futures):
		upbit_balance = 'upbit balance='+str(Upbit.fetch_balance(upbit)) + 'KRW'
		binance_balance = 'binance balance='+str(Binance.fetch_balance(binance)) + 'USDT'
		futures_balance = 'futures balance='+str(Futures.fetch_balance(futures)) + 'USDT'
		
		args = [upbit_balance, binance_balance, futures_balance]
		Telegram.send_message(Telegram.args_to_message(args))
	
	@staticmethod
	def coin_symbols_intersection(upbit, binance, futures):
		upbit_market_symbols = Upbit.fetch_market_symbols(upbit)
		binance_market_symbols = Binance.fetch_market_symbols(binance)
		futures_market_symbols = Futures.fetch_market_symbols(futures)
		
		market_symbols_intersection =  list(set(upbit_market_symbols) & set(binance_market_symbols) & set(futures_market_symbols))
		
		# upbit doesn't update wallet states properly. So I need to manually get rid of them.
		market_symbols_intersection.remove('IOTA') # Upbit
		market_symbols_intersection.remove('ATOM') # Upbit
		
		# upbit withdraw fee expensive (> 1,500KRW)
		market_symbols_intersection.remove('ANKR')
		market_symbols_intersection.remove('BAT')
		market_symbols_intersection.remove('BTC')
		market_symbols_intersection.remove('CHZ')
		market_symbols_intersection.remove('CVC')
		market_symbols_intersection.remove('DOT')
		market_symbols_intersection.remove('ENJ')
		market_symbols_intersection.remove('ETH')
		market_symbols_intersection.remove('KAVA')
		market_symbols_intersection.remove('KNC')
		market_symbols_intersection.remove('LINK')
		market_symbols_intersection.remove('LTC')
		market_symbols_intersection.remove('OMG')
		market_symbols_intersection.remove('SAND')
		market_symbols_intersection.remove('SRM')
		market_symbols_intersection.remove('STORJ')
		market_symbols_intersection.remove('SXP')
		market_symbols_intersection.remove('VET')
		market_symbols_intersection.remove('XTZ')
		market_symbols_intersection.remove('ZRX')

		# binance withdraw fee expensive (> 1,500KRW)
		
		return sorted(market_symbols_intersection)
	
	@staticmethod
	def fetch_min_coin_price_precision(upbit, binance, futures, coin_symbol):
		upbit_price_precision = Upbit.fetch_coin_price_precision(upbit, coin_symbol)
		binance_price_precision = Binance.fetch_coin_price_precision(binance, coin_symbol)
		futures_price_precision = Futures.fetch_coin_price_precision(futures, coin_symbol)
		
		return min(upbit_price_precision, binance_price_precision, futures_price_precision)
	
	@classmethod
	def safe_coin_price(cls, upbit, binance, futures, coin_symbol, coin_price):
		min_price_precision = cls.fetch_min_coin_price_precision(upbit, binance, futures, coin_symbol)
		floor_factor = math.pow(10.0, min_price_precision)
		
		return math.floor(coin_price * floor_factor) / floor_factor
	
	@staticmethod
	def fetch_min_coin_amount_precision(upbit, binance, futures, coin_symbol):
		upbit_amount_precision = Upbit.fetch_coin_amount_precision(upbit, coin_symbol)
		binance_amount_precision = Binance.fetch_coin_amount_precision(binance, coin_symbol)
		futures_amount_precision = Futures.fetch_coin_amount_precision(futures, coin_symbol)
		
		return min(upbit_amount_precision, binance_amount_precision, futures_amount_precision)
	
	@classmethod
	def safe_coin_amount(cls, upbit, binance, futures, coin_symbol, coin_amount):
		min_amount_precision = cls.fetch_min_coin_amount_precision(upbit, binance, futures, coin_symbol)
		min_amount_precision = min(min_amount_precision, 6) # 6 for upbit withdraw precision
		floor_factor = math.pow(10.0, min_amount_precision)
		
		return math.floor(coin_amount * floor_factor) / floor_factor


class Upbit(Exchange):
	@classmethod
	def get_coin_id(cls, coin_symbol):
		return coin_symbol + '/' + cls.KRW_SYMBOL
	
	@staticmethod
	def fetch_server_time(upbit):
		ticker = upbit.public_get_ticker({
			'markets': 'KRW-XRP' # The market kind has no effect. Only used for fetching server time.
		})
		server_time = int(ticker[0]['timestamp'])
		
		return server_time
	
	@staticmethod
	def fetch_market_symbols(upbit):
		upbit_markets = upbit.fetch_markets()
		upbit_symbols = []
		
		for market in upbit_markets:
			if market['quote'] == 'KRW':
				upbit_symbols.append(market['base'])
		
		return upbit_symbols
	
	@classmethod
	def fetch_balance(cls, upbit):
		return upbit.fetch_balance()[cls.KRW_SYMBOL]['free']
	
	@staticmethod
	def fetch_coin_count(upbit, coin_symbol):
		return upbit.fetch_balance()[coin_symbol]['free']
	
	@classmethod
	def fetch_coin_price(cls, upbit, coin_symbol):
		return upbit.fetch_ticker(cls.get_coin_id(coin_symbol))['last']
	
	@classmethod
	def fetch_market_restricts(cls, upbit, coin_symbol):
		upbit.load_markets()
		market = upbit.markets[cls.get_coin_id(coin_symbol)]
		
		return market
	
	@classmethod
	def fetch_coin_price_precision(cls, upbit, coin_symbol):
		restricts = cls.fetch_market_restricts(upbit, coin_symbol)
		price_precision = restricts['precision']['price']
		
		return price_precision
	
	@classmethod
	def safe_coin_price(cls, upbit, coin_symbol, coin_price):
		price_precision = cls.fetch_coin_price_precision(upbit, coin_symbol)
		floor_factor = math.pow(10.0, price_precision)
		
		return math.floor(coin_price * floor_factor) / floor_factor
	
	@classmethod
	def fetch_coin_amount_precision(cls, upbit, coin_symbol):
		restricts = cls.fetch_market_restricts(upbit, coin_symbol)
		quantity_precision = restricts['precision']['amount']
		
		return quantity_precision
	
	@classmethod
	def safe_coin_amount(cls, upbit, coin_symbol, coin_amount):
		amount_precision = cls.fetch_coin_amount_precision(upbit, coin_symbol)
		floor_factor = math.pow(10.0, amount_precision)
		
		return math.floor(coin_amount * floor_factor) / floor_factor
	
	@classmethod
	def is_wallet_limitless(cls, upbit, coin_symbol):
		return upbit.fetch_currency_by_id(coin_symbol)['active']
	
	@classmethod
	def create_market_buy_order(cls, upbit, coin_symbol, coin_count):
		coin_price = cls.fetch_coin_price(upbit, coin_symbol)
		
		# Can't use ccxt.create_market_buy_order: Upbit's market buy order amount is determined by krw, not coins.
		upbit.create_market_order(Upbit.get_coin_id(coin_symbol), 'buy', coin_count, coin_price)
	
	@classmethod
	def create_market_sell_order(cls, upbit, coin_symbol, coin_count):
		upbit.create_market_order(Upbit.get_coin_id(coin_symbol), 'sell', coin_count)


class Binance(Exchange):
	TAKER_FEE = 0.001
	
	@classmethod
	def get_coin_id(cls, coin_symbol):
		return coin_symbol + '/' + cls.USDT_SYMBOL
	
	@classmethod
	def safe_precision(cls, amount):
		min_precision = min(cls.BUY_PRECISION, cls.SELL_PRECISION, cls.WITHDRAW_PRECISION)
		floor_factor = math.pow(10.0, min_precision)
		
		return math.floor(amount * floor_factor) / floor_factor
	
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
	def safe_coin_price(cls, binance, coin_symbol, coin_price):
		price_precision = cls.fetch_coin_price_precision(binance, coin_symbol)
		floor_factor = math.pow(10.0, price_precision)
		
		return math.floor(coin_price * floor_factor) / floor_factor
	
	@classmethod
	def fetch_coin_amount_precision(cls, binance, coin_symbol):
		restricts = cls.fetch_market_restricts(binance, coin_symbol)
		quantity_precision = restricts['precision']['amount']
		
		return quantity_precision
	
	@classmethod
	def safe_coin_amount(cls, binance, coin_symbol, coin_amount):
		amount_precision = cls.fetch_coin_amount_precision(binance, coin_symbol)
		floor_factor = math.pow(10.0, amount_precision)
		
		return math.floor(coin_amount * floor_factor) / floor_factor
	
	@classmethod
	def is_wallet_limitless(cls, binance, coin_symbol):
		configs = binance.sapi_get_capital_config_getall()
		
		for config in configs:
			if config['coin'] == coin_symbol:
				return config['depositAllEnable'] and config['withdrawAllEnable'] and config['trading']
		
		return None
	
	@classmethod
	def create_market_buy_order(cls, binance, coin_symbol, coin_count):
		binance.create_market_buy_order(cls.get_coin_id(coin_symbol), coin_count)  # , {'test':True,})
		
	@classmethod
	def create_market_sell_order(cls, binance, coin_symbol, coin_count):
		binance.create_market_sell_order(cls.get_coin_id(coin_symbol), coin_count)  # , {'test':True,})


class Futures(Exchange):
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
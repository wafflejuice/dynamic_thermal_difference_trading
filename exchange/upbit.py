from exchange.base_exchange import BaseExchange


class Upbit(BaseExchange):
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
	def fetch_coin_amount_precision(cls, upbit, coin_symbol):
		restricts = cls.fetch_market_restricts(upbit, coin_symbol)
		quantity_precision = restricts['precision']['amount']
		
		return quantity_precision
	
	@classmethod
	def is_wallet_limitless(cls, upbit, coin_symbol):
		return upbit.fetch_currency_by_id(coin_symbol)['active']
	
	@classmethod
	def fetch_coin_withdraw_fee(cls, upbit, coin_symbol):
		return upbit.fetch_currency_by_id(coin_symbol)['info']['currency']['withdraw_fee']
	
	@classmethod
	def create_market_buy_order(cls, upbit, coin_symbol, coin_count):
		coin_price = cls.fetch_coin_price(upbit, coin_symbol)
		
		# Can't use ccxt.create_market_buy_order: Upbit's market buy order amount is determined by krw, not coins.
		upbit.create_market_order(Upbit.get_coin_id(coin_symbol), 'buy', coin_count, coin_price)
	
	@classmethod
	def create_market_sell_order(cls, upbit, coin_symbol, coin_count):
		upbit.create_market_order(Upbit.get_coin_id(coin_symbol), 'sell', coin_count)
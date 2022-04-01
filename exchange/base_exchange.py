import abc
import math

from telegram import Telegram


class BaseExchange:
	__metaclass__ = abc.ABCMeta
	
	KRW_SYMBOL = 'KRW'
	USDT_SYMBOL = 'USDT'
	
	EPOCH_TIME_TWO_HOUR_MS = 7200000

	@abc.abstractmethod
	def to_market_code(self, symbol, market):
		pass
	
	@abc.abstractmethod
	def to_symbol(self, market_code):
		pass

	@abc.abstractmethod
	def fetch_server_timestamp(self):
		pass

	@abc.abstractmethod
	def fetch_symbols(self):
		pass

	@abc.abstractmethod
	def fetch_price(self, symbol, market):
		pass
		
	@abc.abstractmethod
	def fetch_balance(self, symbol):
		pass
	
	@abc.abstractmethod
	def is_wallet_withdrawable(self, symbol, network):
		pass

	@abc.abstractmethod
	def is_wallet_depositable(self, symbol, network):
		pass

	@abc.abstractmethod
	def fetch_withdraw_fee(self, symbol, network):
		pass
	
	@abc.abstractmethod
	def withdraw(self, symbol, to_addr, to_tag, amount, network):
		pass

	@abc.abstractmethod
	def wait_withdraw(self, id_):
		pass

	@abc.abstractmethod
	def fetch_txid(self, id_):
		pass
	
	@abc.abstractmethod
	def wait_deposit(self, txid):
		pass
	
	@abc.abstractmethod
	def create_market_buy_order(self, symbol, market, price):
		pass
	
	@abc.abstractmethod
	def create_market_sell_order(self, symbol, market, volume):
		pass
	
	@abc.abstractmethod
	def order_executed_volume(self, symbol, market, id_):
		pass
	
	@abc.abstractmethod
	def is_order_fully_executed(self, symbol, market, id_):
		pass
	
	@abc.abstractmethod
	def wait_order(self, symbol, market, id_):
		pass
	
	@abc.abstractmethod
	def cancel_order(self, symbol, market, id_):
		pass

	@abc.abstractmethod
	def price_filter(self, symbol, market, price):
		pass
	
	@abc.abstractmethod
	def quantity_filter(self, symbol, market, quantity, is_market):
		pass

class ExchangeHelper:
	@staticmethod
	def notify_balance(exchanges):
		notify_string = ''
		for exchange in exchanges:
			notify_string += str(exchange.fetch_balance('KRW')) + 'KRW, ' + str(exchange.fetch_balance('USD')) + 'USD'
			notify_string += Telegram.LINE_BREAK
		
		Telegram.send_message(notify_string)
	
	@staticmethod
	def coin_symbols_intersection(exchanges):
		exchange_market_symbols_list = []
		for ex in exchanges:
			exchange_market_symbols_list.append(ex.fetch_coin_symbols(ex))

		market_symbols_intersection = set()
		for exchange_market_symbols in exchange_market_symbols_list:
			if len(market_symbols_intersection) == 0:
				market_symbols_intersection = set(exchange_market_symbols)
			else:
				market_symbols_intersection |= set(exchange_market_symbols)
				
		return market_symbols_intersection
	
	@staticmethod
	def min_price_precision(symbol, exchanges):
		min_precision = math.inf
		
		for exchange in exchanges:
			precision = exchange.fetch_price_precision(symbol)
			if min_precision > precision:
				min_precision = precision
				
		return min_precision
	
	@staticmethod
	def safe_coin_price(symbol, exchanges, coin_price):
		min_price_precision = ExchangeHelper.min_price_precision(symbol, exchanges)
		floor_factor = math.pow(10.0, min_price_precision)
		
		return math.floor(coin_price * floor_factor) / floor_factor
	
	@staticmethod
	def min_amount_precision(symbol, exchanges):
		min_precision = math.inf
		
		for exchange in exchanges:
			precision = exchange.fetch_amount_precision(symbol)
			if min_precision > precision:
				min_precision = precision
		
		return min_precision
	
	@staticmethod
	def safe_coin_amount(symbol, exchanges, amount):
		min_amount_precision = ExchangeHelper.min_amount_precision(symbol, exchanges)
		# min_amount_precision = min(min_amount_precision, 6) # 6 for upbit withdraw precision
		floor_factor = math.pow(10.0, min_amount_precision)
		
		return math.floor(amount * floor_factor) / floor_factor

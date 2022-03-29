import abc
import math

from exchange.binance import Binance, Futures
from exchange.upbit import Upbit
from telegram import Telegram


class BaseExchange:
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
	@abc.abstractmethod
	def withdraw(coin_symbol, from_ex, to_ex, amount):
		pass

	@staticmethod
	def telegram_me_balance(upbit, binance, futures):
		upbit_balance = 'upbit balance=' + str(Upbit.fetch_balance(upbit)) + 'KRW'
		binance_balance = 'binance balance=' + str(Binance.fetch_balance(binance)) + 'USDT'
		futures_balance = 'futures balance=' + str(Futures.fetch_balance(futures)) + 'USDT'
		
		args = [upbit_balance, binance_balance, futures_balance]
		Telegram.send_message(Telegram.args_to_message(args))
	
	@staticmethod
	def coin_symbols_intersection(upbit, binance, futures):
		upbit_market_symbols = Upbit.fetch_market_symbols(upbit)
		binance_market_symbols = Binance.fetch_market_symbols(binance)
		futures_market_symbols = Futures.fetch_market_symbols(futures)
		
		market_symbols_intersection =  set(upbit_market_symbols) & set(binance_market_symbols) & set(futures_market_symbols)
		
		return market_symbols_intersection
	
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

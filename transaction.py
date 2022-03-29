import time

from exchange.base_exchange import BaseExchange
from exchange.binance import Binance, Futures
from exchange.upbit import Upbit
from telegram import Telegram
import logger

def withdraw(symbol, from_ex, to_ex, to_addr, to_tag, chain, amount):
	withdraw_id = from_ex.withdraw(symbol, to_addr, to_tag, amount, chain)
	# logger.logger.info('withdraw_id : {}'.format(withdraw_id))
	
	if not from_ex.wait_withdraw(withdraw_id):
		return False
	
	withdraw_txid = from_ex.fetch_txid(withdraw_id)
	
	if not to_ex.wait_deposit(withdraw_txid):
		return False

	# logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send upbit to binance complete')
	return True
	
''' Legacy codes below '''

# direction_type 1: Binance->Futures, 2: Futures->Binance
def internal_transfer_usdt(binance, amount_usdt, direction_type):
	start_time = Binance.fetch_server_time(binance)
	
	transaction = binance.sapi_post_futures_transfer({
		'asset': BaseExchange.USDT_SYMBOL,
		'amount': amount_usdt,
		'type': direction_type,
	})
	
	# Check if transaction is finished
	while True:
		futures_transaction_history = binance.sapi_get_futures_transfer({
			'startTime': start_time - BaseExchange.EPOCH_TIME_TWO_HOUR_MS,  # Because timestamp is floor(serverTime) by second, subtract 1 hour
			'current': 1,
			'asset': BaseExchange.USDT_SYMBOL,
		})
		
		# Check tranId & status
		if futures_transaction_history['total'] > 0:
			futures_last_transaction = futures_transaction_history['rows'][-1]
			
			if futures_last_transaction['tranId'] == transaction['tranId'] and futures_last_transaction['status'] == 'CONFIRMED':
				# Transaction is finished
				return
			
def transfer_usdt(binance, amount_usdt):
	internal_transfer_usdt(binance, amount_usdt, 1)
	
def convert_usdt(binance, amount_usdt):
	internal_transfer_usdt(binance, amount_usdt, 2)

def convert_whole(binance, futures):
	futures_usdt_balance_amount = Futures.fetch_balance(futures)
	convert_usdt(binance, futures_usdt_balance_amount)

def send_coin_upbit_to_binance_perfect_hedge(upbit, binance, futures, coin_symbol, coin_count):
	try:
		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send upbit to binance perfect hedge start')
		
		# HIGHLIGHT: 2-1. [Upbit] Buy
		response = Upbit.create_market_buy_order(upbit, coin_symbol, coin_count)
		logger.logger.info('upbit response to coin buy order : {}'.format(response))

		logger.logger.info('upbit coin buy order : {}'.format(coin_count))
		
		# HIGHLIGHT: 2-2. [Futures] Short
		Futures.market_short(futures, coin_symbol, coin_count, False)
		
		logger.logger.info('binance coin fetch : {}'.format(Upbit.fetch_coin_count(upbit, coin_symbol)))

		time.sleep(5)
		
		# HIGHLIGHT: 3. [Upbit->Binance] send
		withdraw(upbit, binance, coin_symbol, coin_count)

		# upbit withdraw fee
		sended_coin_count = coin_count - Upbit.fetch_coin_withdraw_fee(upbit, coin_symbol)
		
		# HIGHLIGHT: 4-1. [Binance] Sell
		Binance.create_market_sell_order(binance, coin_symbol, sended_coin_count)
		
		# HIGHLIGHT: 4-2. [Futures] Long (reduce-only)
		Futures.market_long(futures, coin_symbol, coin_count, True)
		
		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send upbit to binance perfect hedge complete')
		BaseExchange.telegram_me_balance(upbit, binance, futures)
		
	except Exception as e:
		Telegram.send_message(e)
		logger.logger.error(e)
		
		exit()
	
def send_coin_binance_to_upbit_prefect_hedge(upbit, binance, futures, coin_symbol, coin_count):
	try:
		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send binance to upbit perfect hedge start')
		
		# HIGHLIGHT: 2-1. [Binance] Buy
		response = Binance.create_market_buy_order(binance, coin_symbol, coin_count)
		logger.logger.info('binance response to coin buy order : {}'.format(response))

		logger.logger.info('binance coin buy order : {}'.format(coin_count))
		
		# binance taker fee
		bought_coin_count = coin_count * (1.0 - Binance.TAKER_FEE)
		coin_count = BaseExchange.safe_coin_amount(upbit, binance, futures, coin_symbol, bought_coin_count)
		
		logger.logger.info('binance coin estimate : {}'.format(coin_count))
		logger.logger.info('binance coin fetch : {}'.format(Binance.fetch_coin_count(binance, coin_symbol)))
		
		# HIGHLIGHT: 2-2. [Futures] Short
		Futures.market_short(futures, coin_symbol, coin_count, False)
		
		time.sleep(5)
		
		# HIGHLIGHT: 3. [Binance->Upbit] send
		send_binance_to_upbit(upbit, binance, coin_symbol, coin_count)
		
		# binance withdraw fee
		sended_coin_count = coin_count - Binance.fetch_coin_withdraw_fee(binance, coin_symbol)
		
		# HIGHLIGHT: 4-1. [Upbit] Sell
		Upbit.create_market_sell_order(upbit, coin_symbol, sended_coin_count)
		
		# HIGHLIGHT: 4-2. [Futures] Long (reduce-only)
		Futures.market_long(futures, coin_symbol, coin_count, True)

		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send binance to upbit perfect hedge complete')
		BaseExchange.telegram_me_balance(upbit, binance, futures)

	except Exception as e:
		Telegram.send_message(e)
		logger.logger.error(e)
		
		exit()
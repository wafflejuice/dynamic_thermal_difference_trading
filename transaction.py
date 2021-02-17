import time
import asyncio

from exchange import Exchange, Upbit, Binance, Futures
from telegram import Telegram
from config import Config
import logger

# TODO : balance check
async def send_upbit_to_binance(upbit, binance, coin_symbol, amount):
	logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send upbit to binance start')
	
	config = Config.load_config()
	binance_coin_address = config['binance']['address'][coin_symbol] if coin_symbol in config['binance']['address'] else None
	binance_coin_tag = config['binance']['tag'][coin_symbol] if coin_symbol in config['binance']['tag'] else None
	
	if binance_coin_address is None:
		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send upbit to binance : No binance %s address'.format(coin_symbol))
		return

	loop = asyncio.get_event_loop()
	
	upbit_server_time = await loop.run_in_executor(None, Upbit.fetch_server_time, upbit)
	binance_server_time = await loop.run_in_executor(None, Binance.fetch_server_time, binance)
	
	upbit_withdraw = await loop.run_in_executor(None, upbit.withdraw, coin_symbol, amount, binance_coin_address, binance_coin_tag)
	
	# Get Transaction id by withdraw id
	while True:
		# history is chronological sequence
		upbit_withdraw_history = await loop.run_in_executor(None, upbit.fetch_withdrawals, coin_symbol, upbit_server_time - Exchange.EPOCH_TIME_TWO_HOUR_MS, None)
		
		# if withdraw history is not empty
		if upbit_withdraw_history:
			upbit_last_withdraw = upbit_withdraw_history[-1]
			
			# Transaction id is None at first. It is given after accessing the block-chain network
			if upbit_last_withdraw['txid']:
				if upbit_last_withdraw['id'] == upbit_withdraw['id']:
					break
		
		await asyncio.sleep(1)

	while True:
		# history is chronological sequence
		# Don't know when binance gets submission. So start_time must cover long range.
		# Assumption: A transaction time is under 1 hour
		binance_deposit_history = await loop.run_in_executor(None, binance.fetch_deposits, coin_symbol, binance_server_time - Exchange.EPOCH_TIME_TWO_HOUR_MS, None)
		
		# if deposit history is not empty
		if binance_deposit_history:
			binance_last_deposit = binance_deposit_history[-1]
			
			# status: 'pending'->'ok'
			if binance_last_deposit['txid'] == upbit_last_withdraw['txid'] and binance_last_deposit['status'] == 'ok':
				break
		
		await asyncio.sleep(1)

	logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send upbit to binance complete')
	
# TODO : balance check
async def send_binance_to_upbit(upbit, binance, coin_symbol, amount):
	logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send binance to upbit start')

	config = Config.load_config()
	upbit_coin_address = config['upbit']['address'][coin_symbol] if coin_symbol in config['upbit']['address'] else None
	upbit_coin_tag = config['upbit']['tag'][coin_symbol] if coin_symbol in config['upbit']['tag'] else None
	
	if upbit_coin_address is None:
		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send upbit to binance : No binance %s address'.format(coin_symbol))
		return

	loop = asyncio.get_event_loop()
	
	upbit_server_time = await loop.run_in_executor(None, Upbit.fetch_server_time, upbit)
	binance_server_time = await loop.run_in_executor(None, Binance.fetch_server_time, binance)
	
	# response example: {'info': {'success': True, 'id': 'f22641814f3098768efe6e9e7eb253xd'}, 'id': 'f22641814f3098768efe6e9e7eb253xd'}
	binance_withdraw = await loop.run_in_executor(None, binance.withdraw, coin_symbol, amount, upbit_coin_address, upbit_coin_tag)

	# Get Transaction id by withdraw id
	while True:
		# history is chronological sequence
		binance_withdraw_history = await loop.run_in_executor(None, binance.fetch_withdrawals, coin_symbol, binance_server_time - Exchange.EPOCH_TIME_TWO_HOUR_MS, None)
		
		# if withdraw history is not empty
		if binance_withdraw_history:
			binance_last_withdraw = binance_withdraw_history[-1]
			
			# Transaction id is None at first. It is given after accessing the block-chain network
			if binance_last_withdraw['txid']:
				if binance_last_withdraw['id'] == binance_withdraw['id']:
					break
		
		await asyncio.sleep(1)
		
	while True:
		# history is chronological sequence
		# Don't know when upbit gets submission. So start_time must cover long range.
		# Assumption: A transaction time is under 1 hour
		upbit_deposit_history = await loop.run_in_executor(None, upbit.fetch_deposits, coin_symbol, upbit_server_time-Exchange.EPOCH_TIME_TWO_HOUR_MS, None)
		
		# if deposit history is not empty
		if upbit_deposit_history:
			upbit_last_deposit = upbit_deposit_history[-1]
			
			# status: 'PROCESSING'->'ok'
			if upbit_last_deposit['txid'] == binance_last_withdraw['txid'] and upbit_last_deposit['status'] == 'ok':
				break
		
		await asyncio.sleep(1)
	
	logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send binance to upbit complete')
		
# direction_type 1: Binance->Futures, 2: Futures->Binance
# TODO : balance check
async def internal_transfer_usdt(binance, amount_usdt, direction_type):
	loop = asyncio.get_event_loop()
	
	start_time = await loop.run_in_executor(None, Binance.fetch_server_time, binance)
	
	transaction = await loop.run_in_executor(None, binance.sapi_post_futures_transfer, {
		'asset': Exchange.USDT_SYMBOL,
		'amount': amount_usdt,
		'type': direction_type,
	})
	
	# Check if transaction is finished
	while True:
		futures_transaction_history = await loop.run_in_executor(None, binance.sapi_get_futures_transfer, {
			'startTime': start_time - Exchange.EPOCH_TIME_TWO_HOUR_MS,  # Because timestamp is floor(serverTime) by second, subtract 1 hour
			'current': 1,
			'asset': Exchange.USDT_SYMBOL,
		})
		
		# Check tranId & status
		if futures_transaction_history['total'] > 0:
			futures_last_transaction = futures_transaction_history['rows'][-1]
			
			if futures_last_transaction['tranId'] == transaction['tranId'] and futures_last_transaction['status'] == 'CONFIRMED':
				# Transaction is finished
				return
			
async def transfer_usdt(binance, amount_usdt):
	await internal_transfer_usdt(binance, amount_usdt, 1)
	
async def convert_usdt(binance, amount_usdt):
	await internal_transfer_usdt(binance, amount_usdt, 2)

async def convert_whole(binance, futures):
	futures_usdt_balance_amount = await Futures.fetch_balance(futures)
	await convert_usdt(binance, futures_usdt_balance_amount)
	
async def send_coin_upbit_to_binance_perfect_hedge(upbit, binance, futures, coin_symbol, coin_count):
	try:
		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send upbit to binance perfect hedge start')
		
		loop = asyncio.get_event_loop()
		
		# HIGHLIGHT: 2-1. [Upbit] Buy
		await loop.run_in_executor(None, Upbit.create_market_buy_order, upbit, coin_symbol, coin_count)
		
		# HIGHLIGHT: 2-2. [Futures] Short
		await loop.run_in_executor(None, Futures.market_short, futures, coin_symbol, coin_count, False)
		
		# ---------- wait until buy, short done... TODO: so it is needed to be async
		time.sleep(5)
		
		# HIGHLIGHT: 3. [Upbit->Binance] send
		decimal_places = 6 # upbit withdraw_decimal_places <= 6
		upbit_bought_coin_count = await Upbit.fetch_coin_count(upbit, coin_symbol)
		send_upbit_to_binance(upbit, binance, coin_symbol, round(upbit_bought_coin_count, decimal_places))
		
		# HIGHLIGHT: 4-1. [Binance] Sell
		Binance.create_market_sell_order(binance, coin_symbol, coin_count)
		
		# HIGHLIGHT: 4-2. [Futures] Long (reduce-only)
		Futures.market_long(futures, coin_symbol, coin_count, True)
		
		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send upbit to binance perfect hedge complete')
		Exchange.telegram_me_balance(upbit, binance, futures)
		
	except Exception as e:
		Telegram.send_message(e)
		logger.logger.error(e)
	
async def send_coin_binance_to_upbit_prefect_hedge(upbit, binance, futures, coin_symbol, coin_count):
	try:
		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send binance to upbit perfect hedge start')
		
		# HIGHLIGHT: 2-1. [Binance] Buy
		Binance.create_market_buy_order(binance, coin_symbol, coin_count)
		
		# HIGHLIGHT: 2-2. [Futures] Short
		Futures.market_short(futures, coin_symbol, coin_count, False)
		
		# ---------- wait until buy, short done... TODO: so it is needed to be async
		time.sleep(5)
		
		# HIGHLIGHT: 3. [Binance->Upbit] send
		decimal_places = 6
		coin_count = round(coin_count, decimal_places)
		send_binance_to_upbit(upbit, binance, coin_symbol, coin_count)
		
		# HIGHLIGHT: 4-1. [Upbit] Sell
		Upbit.create_market_sell_order(upbit, coin_symbol, coin_count)
		
		# HIGHLIGHT: 4-2. [Futures] Long (reduce-only)
		Futures.market_long(futures, coin_symbol, coin_count, True)

		logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : send binance to upbit perfect hedge complete')
		Exchange.telegram_me_balance(upbit, binance, futures)

	except Exception as e:
		Telegram.send_message(e)
		logger.logger.error(e)
import ccxt
import time

from exchange import Exchange, Upbit, Binance, Futures
import transaction
from premium import Kimp
from premium import Futp
from telegram import Telegram
from config import Config
import logger

def calculate_coin_count_to_transfer(upbit, binance, previous_kimp_stage, coin_symbol, coin_kimp, above_check, min_coin_amount_precisions, buffer_margin_ratio):
	if coin_symbol is not None:
		if above_check:
			is_above = Kimp.is_above(coin_kimp)
			
			if is_above != -1 and is_above > previous_kimp_stage:
				binance_balance_usdt = Binance.fetch_balance(binance)
				binance_balance_with_margin_usdt = binance_balance_usdt * (1.0 - buffer_margin_ratio)
				binance_coin_price_usdt = Binance.fetch_coin_price(binance, coin_symbol)
				
				coin_amount_precision = min_coin_amount_precisions[coin_symbol]
				coin_count_to_transfer = round(binance_balance_with_margin_usdt / binance_coin_price_usdt, coin_amount_precision)
				
				return is_above, coin_count_to_transfer
		
		else:
			is_under = Kimp.is_under(coin_kimp)
			
			if is_under != -1 and is_under < previous_kimp_stage:
				upbit_balance_krw = Upbit.fetch_balance(upbit)
				upbit_balance_with_margin_krw = upbit_balance_krw * (1.0 - buffer_margin_ratio)
				upbit_coin_price_krw = Upbit.fetch_coin_price(upbit, coin_symbol)
				
				coin_amount_precision = min_coin_amount_precisions[coin_symbol]
				coin_count_to_transfer = round(upbit_balance_with_margin_krw / upbit_coin_price_krw, coin_amount_precision)
				
				return is_under, coin_count_to_transfer
	
	return None

def trading_logic_1(upbit, binance, futures):
	coin_symbols = Exchange.coin_symbols_intersection(upbit, binance, futures)
	
	min_coin_amount_precisions = {}
	
	for coin_symbol in coin_symbols:
		# Futures.adjust_leverage(futures, coin_symbol, 5)
		min_coin_amount_precisions[coin_symbol] = Exchange.fetch_min_coin_amount_precision(upbit, binance, futures, coin_symbol)
	
	previous_kimp_stage = 2  # stage 2 -> -2.0%
	buffer_margin_ratio = 0.08  # 8%
	
	Telegram.send_message('start dynamic_tdt1 : balances are')
	Exchange.telegram_me_balance(upbit, binance, futures)
	
	while True:
		try:
			logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : current stage = ' + str(previous_kimp_stage))
			
			# need to send most kimp [Binance -> Upbit]
			if previous_kimp_stage < 3:
				logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : check most kimp')
				
				coin_kimp_dict_list_descending = Kimp.calculate_kimps(upbit, binance, coin_symbols, True)
				
				coin_symbol_to_transfer = None
				coin_kimp = 0.0
				
				for key in coin_kimp_dict_list_descending.keys():
					if Upbit.is_wallet_limitless(upbit, key) and Binance.is_wallet_limitless(binance, key) and Futp.is_acceptable(binance, futures, key):
						coin_symbol_to_transfer = key
						coin_kimp = coin_kimp_dict_list_descending[key]
						
						break
						
				result = calculate_coin_count_to_transfer(upbit, binance, previous_kimp_stage, coin_symbol_to_transfer, coin_kimp, True, min_coin_amount_precisions, buffer_margin_ratio)
				
				if result is not None:
					next_kimp_stage = result[0]
					coin_count_to_transfer = result[1]

					logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : next stage = ' + str(next_kimp_stage))
					
					previous_kimp_stage = next_kimp_stage
					transaction.send_coin_binance_to_upbit_prefect_hedge(upbit, binance, futures, coin_symbol_to_transfer, coin_count_to_transfer)
				
			elif previous_kimp_stage == 3:
				logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : check most kimp & most reverse kimp to make direction')
				
				coin_kimp_dict_list_ascending = Kimp.calculate_kimps(upbit, binance, coin_symbols, False)
				
				most_kimp_coin_symbol = None
				most_kimp = 0.0
				
				most_reverse_kimp_coin_symbol = None
				most_reverse_kimp = 0.0
				
				for key in coin_kimp_dict_list_ascending.keys():
					if Upbit.is_wallet_limitless(upbit, key) and Binance.is_wallet_limitless(binance, key) and Futp.is_acceptable(binance, futures, key):
						most_kimp_coin_symbol = key
						most_kimp = coin_kimp_dict_list_ascending[key]
						
						break
				
				for key in sorted(coin_kimp_dict_list_ascending, reverse=True):
					if Upbit.is_wallet_limitless(upbit, key) and Binance.is_wallet_limitless(binance, key) and Futp.is_acceptable(binance, futures, key):
						most_reverse_kimp_coin_symbol = key
						most_reverse_kimp = coin_kimp_dict_list_ascending[key]
						
						break
				
				transfer_most_kimp = None
				
				if most_kimp_coin_symbol and most_reverse_kimp_coin_symbol:
					transfer_most_kimp = (abs(most_kimp) >= abs(most_reverse_kimp))
				elif most_kimp_coin_symbol and not most_reverse_kimp_coin_symbol:
					transfer_most_kimp = True
				elif most_kimp_coin_symbol and not most_reverse_kimp_coin_symbol:
					transfer_most_kimp = False
				else:
					pass
				
				if transfer_most_kimp is not None:
					result = None
					
					if transfer_most_kimp:
						coin_symbol_to_transfer = most_kimp_coin_symbol
						coin_kimp = most_kimp
						
						result = calculate_coin_count_to_transfer(upbit, binance, previous_kimp_stage, coin_symbol_to_transfer, coin_kimp, True, min_coin_amount_precisions, buffer_margin_ratio)
						
					else:
						coin_symbol_to_transfer = most_reverse_kimp_coin_symbol
						coin_kimp = most_reverse_kimp
						
						result = calculate_coin_count_to_transfer(upbit, binance, previous_kimp_stage, coin_symbol_to_transfer, coin_kimp, False, min_coin_amount_precisions, buffer_margin_ratio)
						
					if result is not None:
						next_kimp_stage = result[0]
						coin_count_to_transfer = result[1]
						
						logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : next stage = ' + str(next_kimp_stage))
						
						previous_kimp_stage = next_kimp_stage
						transaction.send_coin_binance_to_upbit_prefect_hedge(upbit, binance, futures, coin_symbol_to_transfer, coin_count_to_transfer)
			
			# need to send most reverse kimp [Upbit -> Binance]
			else:
				logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : check most reverse kimp')
				
				coin_kimp_dict_list_ascending = Kimp.calculate_kimps(upbit, binance, coin_symbols, False)
				
				coin_symbol_to_transfer = None
				coin_kimp = 0.0
				
				for key in coin_kimp_dict_list_ascending.keys():
					if Upbit.is_wallet_limitless(upbit, key) and Binance.is_wallet_limitless(binance, key) and Futp.is_acceptable(binance, futures, key):
						coin_symbol_to_transfer = key
						coin_kimp = coin_kimp_dict_list_ascending[key]
						
						break
				
				result = calculate_coin_count_to_transfer(upbit, binance, previous_kimp_stage, coin_symbol_to_transfer, coin_kimp, False, min_coin_amount_precisions, buffer_margin_ratio)
				
				if result is not None:
					next_kimp_stage = result[0]
					coin_count_to_transfer = result[1]

					logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : next stage = ' + str(next_kimp_stage))
					
					previous_kimp_stage = next_kimp_stage
					transaction.send_coin_binance_to_upbit_prefect_hedge(upbit, binance, futures, coin_symbol_to_transfer, coin_count_to_transfer)
			
			
			time.sleep(60)
		
		except Exception as e:
			Telegram.send_message(e)
			logger.logger.error(e)

def trading_logic_2(upbit, binance, futures):
	coin_symbols = Exchange.coin_symbols_intersection(upbit, binance, futures)
	min_coin_amount_precisions = {}
	
	for coin_symbol in coin_symbols:
		#Futures.adjust_leverage(futures, coin_symbol, 5)
		min_coin_amount_precisions[coin_symbol] = Exchange.fetch_min_coin_amount_precision(upbit, binance, futures, coin_symbol)
	
	previous_kimp = -0.02 # -2%
	buffer_margin_ratio = 0.05  # 5%
	minimum_difference_ratio = 0.019 # 1.5%
	
	logger.logger.info('start dynamic_tdt2')
	
	while True:
		try:
			logger.logger.info('')
			logger.logger.info(time.strftime('%c', time.localtime(time.time())))
			logger.logger.info('balance : upbit = {}KRW, binance = {}USDT, futures = {}USDT'.format(Upbit.fetch_balance(upbit), Binance.fetch_balance(binance), Futures.fetch_balance(futures)))
			logger.logger.info('previous kimp = {}'.format(previous_kimp))
			
			kimp_list_ascending = Kimp.calculate_kimps(upbit, binance, coin_symbols, False)
			
			logger.logger.info('kimp list : {}'.format(kimp_list_ascending))
			
			most_kimp_coin_symbol = None
			most_kimp = 0.0
			
			most_reverse_kimp_coin_symbol = None
			most_reverse_kimp = 0.0
			
			for key_coin_symbol in kimp_list_ascending.keys():
				if (Upbit.is_wallet_limitless(upbit, key_coin_symbol)
						and Binance.is_wallet_limitless(binance, key_coin_symbol)
						and Futp.is_acceptable(binance, futures, key_coin_symbol)):
					most_reverse_kimp_coin_symbol = key_coin_symbol
					most_reverse_kimp = kimp_list_ascending[key_coin_symbol]
					
					logger.logger.info('most reverse kimp coin found : {}, {}%'.format(most_reverse_kimp_coin_symbol, most_reverse_kimp))
					
					break
			
			for key_coin_symbol in sorted(kimp_list_ascending.keys(), reverse=True):
				if (Upbit.is_wallet_limitless(upbit, key_coin_symbol)
						and Binance.is_wallet_limitless(binance, key_coin_symbol)
						and Futp.is_acceptable(binance, futures, key_coin_symbol)):
					most_kimp_coin_symbol = key_coin_symbol
					most_kimp = kimp_list_ascending[key_coin_symbol]

					logger.logger.info('most kimp coin found : {}, {}%'.format(most_kimp_coin_symbol, most_kimp))
					
					break
			
			if (most_kimp_coin_symbol is not None) and (most_reverse_kimp_coin_symbol is not None):
				transfer_most_kimp = (abs(most_kimp - previous_kimp) >= abs(most_reverse_kimp - previous_kimp))
			elif (most_kimp_coin_symbol is not None) and (most_reverse_kimp_coin_symbol is None):
				transfer_most_kimp = True
			elif (most_kimp_coin_symbol is None) and (most_reverse_kimp_coin_symbol is not None):
				transfer_most_kimp = False
			else:
				transfer_most_kimp = None
				logger.logger.info('no coin has sufficient condition')
				
			if transfer_most_kimp is not None:
				if transfer_most_kimp and abs(most_kimp - previous_kimp) > minimum_difference_ratio:
					coin_symbol_to_transfer = most_kimp_coin_symbol
					previous_kimp = most_kimp
					
					logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : transfer most kimp : coin = ' + str(coin_symbol_to_transfer) + ', kimp = ' + str(most_kimp))
					
					# [b to u]
					binance_balance_usdt = Binance.fetch_balance(binance)
					binance_balance_with_margin_usdt = binance_balance_usdt * (1.0 - buffer_margin_ratio)
					binance_coin_price_usdt = Binance.fetch_coin_price(binance, coin_symbol_to_transfer)
					
					coin_amount_precision = min_coin_amount_precisions[coin_symbol_to_transfer]
					coin_count_to_transfer = round(binance_balance_with_margin_usdt / binance_coin_price_usdt, coin_amount_precision)
					
					transaction.send_coin_binance_to_upbit_prefect_hedge(upbit, binance, futures, coin_symbol_to_transfer, coin_count_to_transfer)
				
				elif not transfer_most_kimp and abs(most_reverse_kimp - previous_kimp) > minimum_difference_ratio:
					coin_symbol_to_transfer = most_reverse_kimp_coin_symbol
					previous_kimp = most_reverse_kimp
					
					logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : transfer most reverse kimp : coin = ' + str(coin_symbol_to_transfer) + ', kimp = ' + str(most_kimp))
					
					upbit_balance_krw = Upbit.fetch_balance(upbit)
					upbit_balance_with_margin_krw = upbit_balance_krw * (1.0 - buffer_margin_ratio)
					upbit_coin_price_krw = Upbit.fetch_coin_price(upbit, coin_symbol_to_transfer)
					
					coin_amount_precision = min_coin_amount_precisions[coin_symbol_to_transfer]
					coin_count_to_transfer = round(upbit_balance_with_margin_krw / upbit_coin_price_krw, coin_amount_precision)
					
					transaction.send_coin_upbit_to_binance_perfect_hedge(upbit, binance, futures, coin_symbol_to_transfer, coin_count_to_transfer)
				
			time.sleep(10)
		
		except Exception as e:
			Telegram.send_message(e)
			logger.logger.error(e)
			
def run():
	config = Config.load_config()
	
	upbit = ccxt.upbit({'apiKey': config['upbit']['key']['api key'], 'secret': config['upbit']['key']['secret key']})
	binance = ccxt.binance({'apiKey': config['binance']['key']['api key'], 'secret': config['binance']['key']['secret key']})
	futures = ccxt.binance({
		'apiKey': config['binance']['key']['api key'],
		'secret': config['binance']['key']['secret key'],
		'enableRateLimit': True,
		'options': {
			'defaultType': 'future',
		},
	})
	
	trading_logic_2(upbit, binance, futures)

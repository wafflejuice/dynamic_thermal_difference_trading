import ccxt
import time

from exchange import Exchange, Upbit, Binance, Futures
import transaction
from premium import Kimp
from premium import Futp
from telegram import Telegram
from config import Config
import logger


def trading_logic_2(upbit, binance, futures):
	coin_symbols = Exchange.coin_symbols_intersection(upbit, binance, futures)
	min_coin_amount_precisions = {}
	
	for coin_symbol in coin_symbols:
		#Futures.adjust_leverage(futures, coin_symbol, 5)
		min_coin_amount_precisions[coin_symbol] = Exchange.fetch_min_coin_amount_precision(upbit, binance, futures, coin_symbol)
	
	previous_kimp = -0.02 # -2%
	buffer_margin_ratio = 0.05  # 5%
	minimum_difference_ratio = 0.02 # 2%
	futp_gap_ratio = 0.006 # 0.6%
	
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
						and Futp.is_acceptable(binance, futures, key_coin_symbol, futp_gap_ratio)):
					most_reverse_kimp_coin_symbol = key_coin_symbol
					most_reverse_kimp = kimp_list_ascending[key_coin_symbol]
					
					logger.logger.info('most reverse kimp coin found : {}, {}%'.format(most_reverse_kimp_coin_symbol, most_reverse_kimp))
					
					break
			
			for key_coin_symbol in sorted(kimp_list_ascending.keys(), reverse=True):
				if (Upbit.is_wallet_limitless(upbit, key_coin_symbol)
						and Binance.is_wallet_limitless(binance, key_coin_symbol)
						and Futp.is_acceptable(binance, futures, key_coin_symbol, futp_gap_ratio)):
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
					
					Telegram.send_message(Telegram.args_to_message(["transfer most kimp", "coin = {}".format(coin_symbol_to_transfer), "kimp = {}%".format(most_kimp)]))
					logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : transfer most kimp : coin = {}, kimp = {}%'.format(coin_symbol_to_transfer, most_kimp))
					
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

					Telegram.send_message(Telegram.args_to_message(["transfer most reverse kimp", "coin = {}".format(coin_symbol_to_transfer), "kimp = {}%".format(most_reverse_kimp)]))
					logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : transfer most kimp : coin = {}, kimp = {}%'.format(coin_symbol_to_transfer, most_reverse_kimp))
					
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

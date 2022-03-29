import ccxt
import time

from exchange.base_exchange import BaseExchange
from exchange.binance import Binance, Futures
from exchange.upbit import Upbit
import transaction
from premium import Kimp
from premium import Futp
from telegram import Telegram
from config import Config
import logger


def trading_logic(upbit, binance, futures):
	config = Config.load_config()
	upbit_exclusion_symbols = config['upbit']['exclusion']
	binance_exclusion_symbols = config['binance']['exclusion']
	
	coin_symbols = BaseExchange.coin_symbols_intersection(upbit, binance, futures)
	
	for symbol in upbit_exclusion_symbols:
		coin_symbols.discard(symbol)
	for symbol in binance_exclusion_symbols:
		coin_symbols.discard(symbol)
		
	coin_symbols = sorted(list(coin_symbols))
	
	for coin_symbol in coin_symbols:
		Futures.adjust_leverage(futures, coin_symbol, 5)
	
	
	previous_stage = 3 # 0.0%
	buffer_margin_ratio = 0.05  # 5%
	futp_gap_ratio = 0.005 # 0.5%
	
	logger.logger.info('start dynamic_tdt2')
	
	while True:
		try:
			logger.logger.info('')
			logger.logger.info(time.strftime('%c', time.localtime(time.time())))
			logger.logger.info('balance : upbit = {}KRW, binance = {}USDT, futures = {}USDT'.format(Upbit.fetch_balance(upbit), Binance.fetch_balance(binance), Futures.fetch_balance(futures)))
			logger.logger.info('previous stage = {}'.format(previous_stage))
			
			kimp_list_ascending = Kimp.calculate_premiums(upbit, binance, coin_symbols, 'krw', 'usd')
			
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
			
			kimp_stage = Kimp.calculate_stage(previous_stage, most_kimp)
			reverse_kimp_stage = Kimp.calculate_stage(previous_stage, most_reverse_kimp)
			
			if (most_kimp_coin_symbol is not None) and (most_reverse_kimp_coin_symbol is not None):
				transfer_most_kimp = abs(kimp_stage - previous_stage) >= abs(reverse_kimp_stage - previous_stage)
			elif (most_kimp_coin_symbol is not None) and (most_reverse_kimp_coin_symbol is None):
				transfer_most_kimp = True
			elif (most_kimp_coin_symbol is None) and (most_reverse_kimp_coin_symbol is not None):
				transfer_most_kimp = False
			else:
				transfer_most_kimp = None
				logger.logger.info('no coin has sufficient condition')
				
			if transfer_most_kimp is not None:
				if transfer_most_kimp and abs(kimp_stage - previous_stage) > 0:
					coin_symbol_to_transfer = most_kimp_coin_symbol
					
					Telegram.send_message(Telegram.args_to_message(["transfer most kimp", "coin = {}".format(coin_symbol_to_transfer), "kimp = {}%".format(most_kimp)]))
					logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : transfer most kimp : coin = {}, kimp = {}%'.format(coin_symbol_to_transfer, most_kimp))
					
					# [b to u]
					transfer_balance_ratio = abs(Kimp.calculate_transfer_balance_ratio(previous_stage, kimp_stage))
					binance_balance_usdt = Binance.fetch_balance(binance) * transfer_balance_ratio
					binance_balance_with_margin_usdt = binance_balance_usdt * (1.0 - buffer_margin_ratio)
					binance_coin_price_usdt = Binance.fetch_coin_price(binance, coin_symbol_to_transfer)
					
					coin_amount_to_transfer = binance_balance_with_margin_usdt / binance_coin_price_usdt
					safe_coin_amount_to_transfer = BaseExchange.safe_coin_amount(upbit, binance, futures, coin_symbol_to_transfer, coin_amount_to_transfer)
					
					transaction.send_coin_binance_to_upbit_prefect_hedge(upbit, binance, futures, coin_symbol_to_transfer, safe_coin_amount_to_transfer)
				
					previous_stage = kimp_stage
				
				elif not transfer_most_kimp and abs(reverse_kimp_stage - previous_stage) > 0:
					coin_symbol_to_transfer = most_reverse_kimp_coin_symbol

					Telegram.send_message(Telegram.args_to_message(["transfer most reverse kimp", "coin = {}".format(coin_symbol_to_transfer), "kimp = {}%".format(most_reverse_kimp)]))
					logger.logger.info(time.strftime('%c', time.localtime(time.time())) + ' : transfer most kimp : coin = {}, kimp = {}%'.format(coin_symbol_to_transfer, most_reverse_kimp))
				
					transfer_balance_ratio = abs(Kimp.calculate_transfer_balance_ratio(previous_stage, reverse_kimp_stage))
					upbit_balance_krw = Upbit.fetch_balance(upbit) * transfer_balance_ratio
					upbit_balance_with_margin_krw = upbit_balance_krw * (1.0 - buffer_margin_ratio)
					upbit_coin_price_krw = Upbit.fetch_coin_price(upbit, coin_symbol_to_transfer)
					
					coin_amount_to_transfer = upbit_balance_with_margin_krw / upbit_coin_price_krw
					safe_coin_amount_to_transfer = BaseExchange.safe_coin_amount(upbit, binance, futures, coin_symbol_to_transfer, coin_amount_to_transfer)
					
					transaction.send_coin_upbit_to_binance_perfect_hedge(upbit, binance, futures, coin_symbol_to_transfer, safe_coin_amount_to_transfer)
				
					previous_stage = reverse_kimp_stage
				
			time.sleep(10)
		
		except Exception as e:
			Telegram.send_message(e)
			logger.logger.error(e)
			
			return
			
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

	trading_logic(upbit, binance, futures)

import time

from exchange.base_exchange import BaseExchange
from exchange.binance import Binance, Futures
from exchange.upbit import Upbit
import transaction
from premium import Premium
from premium import Futp
from telegram import Telegram
from config import Config
import logger
from my_test import upbit_test, binance_test
from premium import Premium


# legacy
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
			
			kimp_list_ascending = Premium.fetch_premiums(upbit, binance, coin_symbols, 'krw', 'usd')
			
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
			
			kimp_stage = Premium.calculate_stage(previous_stage, most_kimp)
			reverse_kimp_stage = Premium.calculate_stage(previous_stage, most_reverse_kimp)
			
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
					transfer_balance_ratio = abs(Premium.calculate_transfer_balance_ratio(previous_stage, kimp_stage))
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
				
					transfer_balance_ratio = abs(Premium.calculate_transfer_balance_ratio(previous_stage, reverse_kimp_stage))
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

def logic(market1, ex1, addresses1, tags1, market2, ex2, addresses2, tags2):
	# lot_size = {'USDT': 500, 'KRW': 600000}
	# threshold = {'USDT': 10, 'KRW': 12000}
	lot_size = {'USDT' : 100, 'KRW':120000}
	threshold = {'USDT' : 1, 'KRW':1200}

	balance1 = ex1.fetch_balance(market1)
	balance2 = ex2.fetch_balance(market2)
	
	print(balance1)
	print(balance2)
	
	lot_size1 = min(balance1, lot_size[market1])
	lot_size2 = min(balance2, lot_size[market2])
	
	start_time_s = time.time()
	term_s = 10
	while True:
		if time.time() - start_time_s < term_s:
			continue
		start_time_s = time.time()
		
		max_expected_profit_1_to_2 = (None, None, 0)
		max_expected_profit_2_to_1 = (None, None, 0)
		
		if balance1 >= lot_size[market1]:
			max_expected_profit_1_to_2 = Premium.fetch_max_expected_profit(lot_size1, market1, ex1, addresses1, market2, ex2, addresses2)
		if balance2 >= lot_size[market2]:
			max_expected_profit_2_to_1 = Premium.fetch_max_expected_profit(lot_size2, market2, ex2, addresses2, market1, ex1, addresses1)
		
		print(max_expected_profit_1_to_2)
		print(max_expected_profit_2_to_1)
		
		is_1_to_2 = False
		
		if max_expected_profit_1_to_2[2] < threshold[market2] and max_expected_profit_2_to_1[2] < threshold[market1]:
			continue
		elif max_expected_profit_1_to_2[2] < threshold[market2]:
			is_1_to_2 = False
		elif max_expected_profit_2_to_1[2] < threshold[market1]:
			is_1_to_2 = True
		else:
			import currency
			usd_krw_rate = currency.fetch_usd_krw_rate()
			rate_1_to_2 = usd_krw_rate if market1 == 'USDT' and market2 == 'KRW' else 1 / usd_krw_rate
		
			max_expected_profit_2_to_1[2] *= rate_1_to_2
			
			if max_expected_profit_2_to_1[2] > max_expected_profit_1_to_2[2]:
				is_1_to_2 = False
			else:
				is_1_to_2 = True
		
		if is_1_to_2:
			candidate_symbol, candidate_network, expected_profit = max_expected_profit_1_to_2
			from_lot_size = lot_size1
			from_market = market1
			from_ex = ex1
			from_balance = balance1
			to_market = market2
			to_ex = ex2
			to_addr = addresses2[candidate_symbol][candidate_network]
			to_tag = tags2[candidate_symbol][candidate_network]
			to_balance = balance2
		else:
			candidate_symbol, candidate_network, expected_profit = max_expected_profit_2_to_1
			from_lot_size = lot_size2
			from_market = market2
			from_ex = ex2
			from_balance = balance2
			to_market = market1
			to_ex = ex1
			to_addr = addresses1[candidate_symbol][candidate_network]
			to_tag = tags1[candidate_symbol][candidate_network]
			to_balance = balance1
		
		print(f'candidate_symbol={candidate_symbol}, candidate_network={candidate_network}, expected_profit={expected_profit}')
		
		price = from_lot_size
		from_order_id = from_ex.create_market_buy_order(candidate_symbol, from_market, price)
		from_order_result = from_ex.wait_order(candidate_symbol, from_market, from_order_id)
		executed_volume = from_ex.order_executed_volume(candidate_symbol, from_market, from_order_id)
		network = None
		withdraw_id = from_ex.withdraw(candidate_symbol, to_addr, to_tag, executed_volume, network)
		txid = from_ex.fetch_txid(withdraw_id)
		deposit_result = to_ex.wait_deposit(txid)
		
		if not deposit_result:
			print('deposit rejected')
			return False
		
		deposit_volume = to_ex.fetch_deposit_amount(txid)
		to_order_id = to_ex.create_market_sell_order(candidate_symbol, to_market, deposit_volume)
		to_order_result = to_ex.wait_order(candidate_symbol, to_market, to_order_id)
		
		return True

def run():
	# symbol = 'KAVA'
	# market = 'KRW'
	
	# upbit.basic_tests(symbol, market)
	# binance.basic_tests('BTC', 'USDT')
	# upbit.deposit_txid_case('0x89577d5e58936e003bfcb82f75c49ed25596e2151e20527bbc555e5f4359092e')
	# binance.deposit_txid_case('34C272976A54D73AACDCB4C4993C83B69AB79705C43018FBB2431D1B0B696E4D')
	# upbit.test_scenario(symbol, market)
	# binance.test_scenario(symbol, market)
	
	# binance.market_sell('KAVA', 'USDT', 107.78905100)
	
	config = Config.load_config()
	
	upbit_api_key = config['upbit']['key']['api key']
	upbit_secret_key = config['upbit']['key']['secret key']
	upbit_addresses = config['upbit']['address']
	upbit_tags = config['upbit']['tag']
	upbit = Upbit(upbit_api_key, upbit_secret_key, upbit_addresses)
	
	binance_api_key = config['binance']['key']['api key']
	binance_secret_key = config['binance']['key']['secret key']
	binance = Binance(binance_api_key, binance_secret_key)
	binance_addresses = config['binance']['address']
	binance_tags = config['binance']['tag']
	
	res = logic('KRW', upbit, upbit_addresses, upbit_tags, 'USDT', binance, binance_addresses, binance_tags)
	print(res)
	
	Telegram.send_message(str(res))
	

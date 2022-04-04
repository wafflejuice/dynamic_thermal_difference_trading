import time

from exchange.binance import Binance, Futures
from exchange.upbit import Upbit
from premium import Premium
from telegram import Telegram
from config import Config
import logger
from my_test import upbit_test, binance_test


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
		
		to_tag = None
		if is_1_to_2:
			candidate_symbol, candidate_network, expected_profit = max_expected_profit_1_to_2
			from_lot_size = lot_size1
			from_market = market1
			from_ex = ex1
			from_balance = balance1
			to_market = market2
			to_ex = ex2
			to_addr = addresses2[candidate_symbol][candidate_network]
			if candidate_symbol in tags2[candidate_symbol].keys() and candidate_network in tags2[candidate_symbol].keys():
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
			if candidate_symbol in tags1[candidate_symbol].keys() and candidate_network in tags1[candidate_symbol].keys():
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
	
	# upbit_api_key = config['upbit']['key']['api key']
	# upbit_secret_key = config['upbit']['key']['secret key']
	# upbit_addresses = config['upbit']['address']
	# upbit_tags = config['upbit']['tag']
	# upbit = Upbit(upbit_api_key, upbit_secret_key, upbit_addresses)
	
	binance_api_key = config['binance']['key']['api key']
	binance_secret_key = config['binance']['key']['secret key']
	binance_addresses = config['binance']['address']
	binance_tags = config['binance']['tag']
	binance = Binance(binance_api_key, binance_secret_key)
	
	print(binance.is_wallet_withdrawable('STX', 'STX'))
	return
	
	res = logic('KRW', upbit, upbit_addresses, upbit_tags, 'USDT', binance, binance_addresses, binance_tags)
	print(res)
	
	Telegram.send_message(str(res))
	

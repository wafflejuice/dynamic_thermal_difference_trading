from config import Config
from exchange.upbit import Upbit
from exchange.binance import Binance
import time

def deposit_txid_case(txid):
	config = Config.load_config()
	upbit_api_key = config['upbit']['key']['api key']
	upbit_secret_key = config['upbit']['key']['secret key']
	upbit = Upbit(upbit_api_key, upbit_secret_key)
	
	print(upbit.wait_deposit(txid))
	print(upbit.wait_deposit(txid.lower()))
	print(upbit.wait_deposit(txid.upper()))
	

def basic_tests(symbol, market):
	config = Config.load_config()
	
	upbit_api_key = config['upbit']['key']['api key']
	upbit_secret_key = config['upbit']['key']['secret key']
	upbit = Upbit(upbit_api_key, upbit_secret_key)
	
	print(f"upbit.to_market_code(symbol, market) = {upbit.to_market_code(symbol, market)}")
	print(f"upbit.to_symbol('USDT-BTC') = {upbit.to_symbol('USDT-BTC')}")
	print(f"upbit.fetch_server_timestamp() = {upbit.fetch_server_timestamp()}")
	print(f"upbit.fetch_symbols() = {upbit.fetch_symbols()}")
	print(f"upbit.fetch_price(symbol, market) = {upbit.fetch_price(symbol, market)}")
	print(f"upbit.fetch_balance(symbol) = {upbit.fetch_balance(symbol)}")
	print(f"upbit.is_wallet_withdrawable(symbol) = {upbit.is_wallet_withdrawable(symbol)}")
	print(f"upbit.is_wallet_depositable(symbol) = {upbit.is_wallet_depositable(symbol)}")
	print(f"upbit.fetch_withdraw_fee(symbol) = {upbit.fetch_withdraw_fee(symbol)}")
	print(f"upbit.fetch_withdraw_fee(symbol) * upbit.fetch_price(symbol, market) = {upbit.fetch_withdraw_fee(symbol) * upbit.fetch_price(symbol, market)}")

def test_scenario(symbol, market):
	config = Config.load_config()
	
	upbit_api_key = config['upbit']['key']['api key']
	upbit_secret_key = config['upbit']['key']['secret key']
	upbit = Upbit(upbit_api_key, upbit_secret_key)
	
	binance_api_key = config['binance']['key']['api key']
	binance_secret_key = config['binance']['key']['secret key']
	binance = Binance(binance_api_key, binance_secret_key)
	
	binance_addr = config['binance']['address'][symbol]
	binance_tag = None
	if symbol in config['binance']['tag'].keys():
		binance_tag = config['binance']['tag'][symbol]
	
	print(binance_addr)
	print(binance_tag)
	
	# uuid = upbit.create_market_buy_order(symbol, market, 600000)
	# uuid = '706196a6-69d5-4339-88f0-21fd6f08b1ad'
	uuid = '867a5948-fa6d-4865-81ba-f3fb9f46808c'
	print(uuid)
	
	print(upbit.wait_order(symbol, uuid))
	withdraw_amount = upbit.order_executed_volume(symbol, uuid)
	print(withdraw_amount)
	
	# uuid = upbit.withdraw(symbol, binance_addr, binance_tag, withdraw_amount)
	# uuid = 'ab6e79dc-1003-41c4-85b0-58ef738ef586'
	uuid = '35e9f460-2e10-4b48-a55b-027957aaef2a'
	print(uuid)
	
	# Don't need it. Sometimes, even though withdrawal is done, upbit does not show the state properly.
	# print(upbit.wait_withdraw(uuid))
	
	txid = upbit.fetch_txid(uuid)
	print(txid)
	
	print(time.time())
	print(binance.wait_deposit(txid))
	print(time.time())
	
	'''
	print(upbit.wait_deposit(txid))
	uuid = upbit.create_market_sell_order(symbol, market, 1)
	print(upbit.wait_order(symbol, uuid))
	print(upbit.cancel_order(symbol, uuid))
	'''
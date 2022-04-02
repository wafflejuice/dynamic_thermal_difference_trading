from config import Config
from exchange.binance import Binance

def market_sell(symbol, market, volume):
	config = Config.load_config()
	
	binance_api_key = config['binance']['key']['api key']
	binance_secret_key = config['binance']['key']['secret key']
	binance = Binance(binance_api_key, binance_secret_key)

	print(binance.create_market_sell_order(symbol, market, volume))

def deposit_txid_case(txid):
	config = Config.load_config()
	
	binance_api_key = config['binance']['key']['api key']
	binance_secret_key = config['binance']['key']['secret key']
	binance = Binance(binance_api_key, binance_secret_key)
	
	print(binance.wait_deposit(txid))
	print(binance.wait_deposit(txid.lower()))
	print(binance.wait_deposit(txid.upper()))
	
def basic_tests(symbol, market):
	config = Config.load_config()
	
	binance_api_key = config['binance']['key']['api key']
	binance_secret_key = config['binance']['key']['secret key']
	binance = Binance(binance_api_key, binance_secret_key)
	
	print(f"binance.to_market_code(symbol, market) = {binance.to_market_code(symbol, market)}")
	print(f"binance.to_symbol('BTCUSDT') = {binance.to_symbol('BTCUSDT')}")
	print(f"binance.fetch_server_timestamp() = {binance.fetch_server_timestamp()}")
	print(f"binance.fetch_symbols() = {binance.fetch_symbols()}")
	print(f"binance.fetch_price(symbol, market) = {binance.fetch_price(symbol, market)}")
	print(f"binance.fetch_balance(symbol) = {binance.fetch_balance(symbol)}")
	print(f"binance.is_wallet_withdrawable(symbol) = {binance.is_wallet_withdrawable(symbol)}")
	print(f"binance.is_wallet_depositable(symbol) = {binance.is_wallet_depositable(symbol)}")
	print(f"binance.fetch_withdraw_fee(symbol) = {binance.fetch_withdraw_fee(symbol)}")
	print(f"binance.fetch_withdraw_fee(symbol) * binance.fetch_price(symbol, market) = {binance.fetch_withdraw_fee(symbol) * binance.fetch_price(symbol, market)}")
	
def test_scenario(symbol, market):
	config = Config.load_config()
	
	binance_api_key = config['binance']['key']['api key']
	binance_secret_key = config['binance']['key']['secret key']
	binance = Binance(binance_api_key, binance_secret_key)
	
	upbit_addr = config['upbit']['address'][symbol]
	upbit_tag = None
	if symbol in config['upbit']['tag'].keys():
		upbit_tag = config['upbit']['tag'][symbol]
	
	print(upbit_addr)
	print(upbit_tag)
	
	uuid = binance.create_market_buy_order(symbol, market, 900000)
	# uuid = ''
	print(uuid)
	
	print(binance.wait_order(symbol, uuid))
	
	order_executed_volume = binance.order_executed_volume(symbol, uuid)
	print(order_executed_volume)
	
	withdraw_amount = order_executed_volume - binance.fetch_withdraw_fee(symbol)
	print(withdraw_amount)
	
	uuid = binance.withdraw(symbol, upbit_addr, upbit_tag, withdraw_amount)
	# uuid = ''
	print(uuid)
	
	# print(binance.wait_withdraw(uuid))
	
	txid = binance.fetch_txid(uuid)
	print(txid)
	
	'''
	print(binance.wait_deposit(txid))
	uuid = binance.create_market_sell_order(symbol, market, 1)
	print(binance.wait_order(symbol, uuid))
	print(binance.cancel_order(symbol, uuid))
	'''
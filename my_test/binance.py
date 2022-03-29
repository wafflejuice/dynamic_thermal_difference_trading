from config import Config
from exchange.binance import Binance

def basic_tests():
	config = Config.load_config()
	
	binance_api_key = config['binance']['key']['api key']
	binance_secret_key = config['binance']['key']['secret key']
	binance = Binance(binance_api_key, binance_secret_key)
	
	symbol = 'XEM'
	market = 'KRW'
	
	print(binance.to_market_code(market, symbol))
	print(binance.to_symbol('KRW-BTC'))
	print(binance.fetch_server_timestamp())
	print(binance.fetch_symbols())
	print(binance.fetch_price(symbol, market))
	print(binance.fetch_balance(symbol))
	print(binance.is_wallet_withdrawable(symbol))
	print(binance.is_wallet_depositable(symbol))
	print(binance.fetch_withdraw_fee(symbol))
	print(binance.fetch_withdraw_fee(symbol) * binance.fetch_price(symbol, market))
	
def test_scenario():
	config = Config.load_config()
	
	binance_api_key = config['binance']['key']['api key']
	binance_secret_key = config['binance']['key']['secret key']
	binance = Binance(binance_api_key, binance_secret_key)
	
	symbol = 'XEM'
	market = 'KRW'
	
	upbit_addr = config['binance']['address'][symbol]
	upbit_tag = None
	if symbol in config['binance']['tag'].keys():
		upbit_tag = config['binance']['tag'][symbol]
	
	print(upbit_addr)
	print(upbit_tag)
	
	uuid = binance.create_market_buy_order(symbol, market, 900000)
	# uuid = ''
	print(uuid)
	
	print(binance.wait_order(uuid))
	
	order_executed_volume = binance.order_executed(uuid)
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
	print(binance.wait_order(uuid))
	print(binance.cancel_order(uuid))
	'''
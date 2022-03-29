from config import Config
from exchange.upbit import Upbit

def basic_tests():
	config = Config.load_config()
	
	upbit_api_key = config['upbit']['key']['api key']
	upbit_secret_key = config['upbit']['key']['secret key']
	upbit = Upbit(upbit_api_key, upbit_secret_key)
	
	symbol = 'XEM'
	market = 'KRW'
	
	print(upbit.to_market_code(market, symbol))
	print(upbit.to_symbol('KRW-BTC'))
	print(upbit.fetch_server_timestamp())
	print(upbit.fetch_symbols())
	print(upbit.fetch_price(symbol, market))
	print(upbit.fetch_balance(symbol))
	print(upbit.is_wallet_withdrawable(symbol))
	print(upbit.is_wallet_depositable(symbol))
	print(upbit.fetch_withdraw_fee(symbol))
	print(upbit.fetch_withdraw_fee(symbol) * upbit.fetch_price(symbol, market))
	
def test_scenario():
	config = Config.load_config()
	
	upbit_api_key = config['upbit']['key']['api key']
	upbit_secret_key = config['upbit']['key']['secret key']
	upbit = Upbit(upbit_api_key, upbit_secret_key)
	
	symbol = 'XEM'
	market = 'KRW'
	
	binance_addr = config['binance']['address'][symbol]
	binance_tag = None
	if symbol in config['binance']['tag'].keys():
		binance_tag = config['binance']['tag'][symbol]
	
	print(binance_addr)
	print(binance_tag)
	
	# uuid = upbit.create_market_buy_order(symbol, market, 900000)
	uuid = '706196a6-69d5-4339-88f0-21fd6f08b1ad'
	print(uuid)
	
	print(upbit.wait_order(uuid))
	
	order_executed_volume = upbit.order_executed(uuid)
	print(order_executed_volume)
	
	withdraw_amount = order_executed_volume - upbit.fetch_withdraw_fee(symbol)
	print(withdraw_amount)
	
	# uuid = upbit.withdraw(symbol, binance_addr, binance_tag, withdraw_amount)
	uuid = 'ab6e79dc-1003-41c4-85b0-58ef738ef586'
	print(uuid)
	
	# Don't need it. Sometimes, even though withdrawal is done, upbit does not show the state properly.
	# print(upbit.wait_withdraw(uuid))
	
	txid = upbit.fetch_txid(uuid)
	print(txid)
	
	'''
	print(upbit.wait_deposit(txid))
	uuid = upbit.create_market_sell_order(symbol, market, 1)
	print(upbit.wait_order(uuid))
	print(upbit.cancel_order(uuid))
	'''
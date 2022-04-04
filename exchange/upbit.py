from exchange.base_exchange import BaseExchange

import jwt
import uuid
import hashlib
from urllib.parse import urlencode
import requests
import time


class Upbit(BaseExchange):
	KRW_SYMBOL = 'KRW'
	
	def __init__(self, api_key, secret_key, addresses):
		self._api_key = api_key
		self._secret_key = secret_key
		
		self._withdraw_fees = self._fetch_withdraw_fees(addresses)
		# print(self._withdraw_fees)
		# self._withdraw_fees = {'XRP': {'XRP': 1.0}, 'CVC': {'ETH': 93.0}, 'WAVES': {'WAVES': 0.001}, 'ARDR': {'ARDR': 2.0}, 'REP': {'ETH': 3.4}, 'NEO': {'NEO3': 0.1}, 'MFT': {'ETH': 3408.0}, 'IOST': {'IOST': 0.0}, 'STPT': {'ETH': 299.0}, 'MBL': {'ONT': 600.0}, 'STMX': {'ETH': 1689.0}, 'PLA': {'ETH': 27.0}, 'CELO': {'CELO': 2.0}, 'STX': {'STX': 10.0}}
	
	def to_market_code(self, symbol, market):
		return '{}-{}'.format(market, symbol)
	
	# ex. 'KRW-ETH' to 'ETH'
	def to_symbol(self, market_code, market=None):
		return market_code.split('-')[1]
	
	def to_market(self, market_code, symbol=None):
		return market_code.split('-')[0]
	
	def _get_ticker(self, market_code):
		url = "https://api.upbit.com/v1/ticker"
		query = {"markets": market_code}
		res = requests.request("GET", url, params=query)
		
		return res.json()
	
	def fetch_server_timestamp(self):
		ticker = self._get_ticker(self.to_market_code('BTC', 'KRW'))
		timestamp_ms = int(ticker[0]['timestamp'])
		
		return timestamp_ms
	
	def _get_market_all(self):
		url = "https://api.upbit.com/v1/market/all?isDetails=false"
		headers = {"Accept": "application/json"}
		res = requests.request("GET", url, headers=headers)
		
		return res.json()
	
	def fetch_market_codes(self):
		market_all = self._get_market_all()
		market_codes = list(map(lambda x: x['market'], market_all))
		
		return market_codes
		
	def fetch_symbols(self):
		market_codes = self._get_market_all()
		symbols = list(map(lambda x: self.to_symbol(x['market']), market_codes))
		
		return symbols
	
	def fetch_price(self, symbol, market):
		ticker = self._get_ticker(self.to_market_code(symbol, market))
		
		return float(ticker[0]['trade_price'])
		
	def fetch_prices(self, market):
		market_codes = self.fetch_market_codes()
		market_codes = list(filter(lambda x: self.to_market(x)==market, market_codes))
		tickers = self._get_ticker(', '.join(market_codes))
		
		prices = {}
		for ticker in tickers:
			prices[self.to_symbol(ticker['market'], market)] = ticker['trade_price']
		
		return prices
	
	def _fetch_balance(self):
		url = "https://api.upbit.com/v1/accounts"
		payload = {
			'access_key': self._api_key,
			'nonce': str(uuid.uuid4()),
		}
		
		jwt_token = jwt.encode(payload, self._secret_key)
		authorize_token = 'Bearer {}'.format(jwt_token)
		headers = {"Authorization": authorize_token}
		
		res = requests.get(url, headers=headers)
		
		return res.json()
	
	def fetch_balance(self, symbol):
		balance = self._fetch_balance()
		
		for arg in balance:
			if arg['currency'] == symbol:
				return float(arg['balance'])
			
		return None
	
	def _get_withdraws_chance(self, currency):
		url = 'https://api.upbit.com/v1/withdraws/chance'
		query = {
			'currency': currency,
		}
		query_string = urlencode(query).encode()
		
		m = hashlib.sha512()
		m.update(query_string)
		query_hash = m.hexdigest()
		
		payload = {
			'access_key': self._api_key,
			'nonce': str(uuid.uuid4()),
			'query_hash': query_hash,
			'query_hash_alg': 'SHA512',
		}
		
		jwt_token = jwt.encode(payload, self._secret_key)
		authorize_token = 'Bearer {}'.format(jwt_token)
		headers = {"Authorization": authorize_token}
		
		res = requests.get(url, params=query, headers=headers)
		
		return res.json()
		
	def is_wallet_withdrawable(self, symbol, network=None):
		res = self._get_withdraws_chance(symbol)
		is_working = res['currency']['wallet_state'] == 'working'
		is_withdrawable = 'withdraw' in res['currency']['wallet_support']
		# remaining_daily = float(res['withdraw_limit']['remaining_daily'])
		can_withdraw = res['withdraw_limit']['can_withdraw']
		
		# return is_working and is_withdrawable and amount <= remaining_daily and can_withdraw
		return is_working and is_withdrawable and can_withdraw
		
	def is_wallet_depositable(self, symbol, network=None):
		res = self._get_withdraws_chance(symbol)
		is_working = res['currency']['wallet_state'] == 'working'
		is_depositable = 'deposit' in res['currency']['wallet_support']
		
		return is_working and is_depositable
	
	def fetch_withdraw_fee(self, symbol, network=None):
		res = self._get_withdraws_chance(symbol)
		
		return float(res['currency']['withdraw_fee'])

	def _fetch_withdraw_fees(self, addresses):
		symbols = self.fetch_symbols()
		withdraw_fees = dict()
		for symbol in symbols:
			if symbol in addresses.keys():
				withdraw_fees[symbol] = {list(addresses[symbol].keys())[0]: self.fetch_withdraw_fee(symbol)}
			# else:
			# 	withdraw_fees[symbol] = {symbol:self.fetch_withdraw_fee(symbol)}
		
		return withdraw_fees
		
	def fetch_withdraw_fees(self, addresses):
		return self._withdraw_fees
	
	def _fetch_withdraw_info(self, symbol):
		url = "https://api.upbit.com/v1/withdraws/chance"
		query = {
			'currency': symbol,
		}
		query_string = urlencode(query).encode()
		
		m = hashlib.sha512()
		m.update(query_string)
		query_hash = m.hexdigest()
		
		payload = {
			'access_key': self._api_key,
			'nonce': str(uuid.uuid4()),
			'query_hash': query_hash,
			'query_hash_alg': 'SHA512',
		}
		
		jwt_token = jwt.encode(payload, self._secret_key)
		authorize_token = 'Bearer {}'.format(jwt_token)
		headers = {"Authorization": authorize_token}
		
		res = requests.get(url, params=query, headers=headers)
		
		return res.json()
	
	def _post_withdraws_coin(self, currency, amount, address, secondary_address, transaction_type):
		url = 'https://api.upbit.com/v1/withdraws/coin'
		query = {
			'currency': currency,
			'amount': amount,
			'address': address,
			# 'secondary_address': secondary_address,
			'transaction_type': transaction_type,
		}
		if secondary_address is not None:
			query['secondary_address'] = secondary_address
		
		query_string = urlencode(query).encode()
		
		m = hashlib.sha512()
		m.update(query_string)
		query_hash = m.hexdigest()
		
		payload = {
			'access_key': self._api_key,
			'nonce': str(uuid.uuid4()),
			'query_hash': query_hash,
			'query_hash_alg': 'SHA512',
		}
		
		jwt_token = jwt.encode(payload, self._secret_key)
		authorize_token = 'Bearer {}'.format(jwt_token)
		headers = {"Authorization": authorize_token}
		
		res = requests.post(url, params=query, headers=headers)
		
		return res.json()
	
	def withdraw(self, symbol, to_addr, to_tag, amount, network=None):
		amount -= self.fetch_withdraw_fee(symbol)
		amount = self.quantity_filter(None, None, amount, None)
		
		res = self._post_withdraws_coin(symbol, amount, to_addr, to_tag, 'default')
		
		return res['uuid']
	
	def _get_withdraw(self, uuid_, txid, currency):
		url = 'https://api.upbit.com/v1/withdraw'
		query = {
			# 'uuid': uuid_,
			# 'txid': txid,
			# 'currency': currency,
		}
		if uuid_ is not None:
			query['uuid'] = uuid_
		if txid is not None:
			query['txid'] = txid
		if currency is not None:
			query['currency'] = currency
			
		query_string = urlencode(query).encode()
		
		m = hashlib.sha512()
		m.update(query_string)
		query_hash = m.hexdigest()
		
		payload = {
			'access_key': self._api_key,
			'nonce': str(uuid.uuid4()),
			'query_hash': query_hash,
			'query_hash_alg': 'SHA512',
		}
		
		jwt_token = jwt.encode(payload, self._secret_key)
		authorize_token = 'Bearer {}'.format(jwt_token)
		headers = {"Authorization": authorize_token}
		
		res = requests.get(url, params=query, headers=headers)
		
		return res.json()
	
	def wait_withdraw(self, id_):
		withdraw_response = self._get_withdraw(id_, None, None)
		
		start_time_s = time.time()
		term_s = 1
		while True:
			if time.time() - start_time_s < term_s:
				continue
			
			if withdraw_response['state'].lower() == 'done':
				return True
			elif withdraw_response['state'].lower() in ['rejected', 'canceled']:
				return False
			
			withdraw_response = self._get_withdraw(id_, None, None)
			start_time_s = time.time()
		
		return False
	
	def fetch_txid(self, id_):
		res = self._get_withdraw(id_, None, None)
		
		start_time_s = time.time()
		term_s = 1
		
		while True:
			if time.time() - start_time_s < term_s:
				continue
				
			if res['txid'] is not None:
				return res['txid']
			
			res = self._get_withdraw(id_, None, None)
			start_time_s = time.time()
		
		return None
	
	def _get_deposit(self, uuid_, txid, currency):
		url = 'https://api.upbit.com/v1/deposit'
		query = {
			# 'uuid': uuid_,
			# 'txid': txid,
			# 'currency': currency
		}
		
		if uuid_ is not None:
			query['uuid'] = uuid_
		if txid is not None:
			query['txid'] = txid
		if currency is not None:
			query['currency'] = currency
			
		query_string = urlencode(query).encode()
		
		m = hashlib.sha512()
		m.update(query_string)
		query_hash = m.hexdigest()
		
		payload = {
			'access_key': self._api_key,
			'nonce': str(uuid.uuid4()),
			'query_hash': query_hash,
			'query_hash_alg': 'SHA512',
		}
		
		jwt_token = jwt.encode(payload, self._secret_key)
		authorize_token = 'Bearer {}'.format(jwt_token)
		headers = {"Authorization": authorize_token}
		
		res = requests.get(url, params=query, headers=headers)
		
		return res.json()
	
	def wait_deposit(self, txid):
		deposit_response = self._get_deposit(None, txid, None)
		
		start_time_s = time.time()
		term_s = 1
		while True:
			if time.time() - start_time_s < term_s:
				continue
			
			if deposit_response['state'].lower() == 'accepted':
				return True
			elif deposit_response['state'].lower() in ['rejected']:
				return False
			
			deposit_response = self._get_deposit(None, txid, None)
			start_time_s = time.time()
		
		return False
	
	def fetch_deposit_amount(self, txid):
		deposit_response = self._get_deposit(None, txid, None)
		
		return float(deposit_response['amount'])
	
	def _post_orders(self, symbol, market, side, volume, price, ord_type):
		url = 'https://api.upbit.com/v1/orders'
		query = {
			'market': self.to_market_code(symbol, market),
			'side': side,
			# 'volume': volume,
			# 'price': price,
			'ord_type': ord_type,
		}
		
		if volume is not None:
			query['volume'] = volume
		if price is not None:
			query['price'] = price
		
		query_string = urlencode(query).encode()
		
		m = hashlib.sha512()
		m.update(query_string)
		query_hash = m.hexdigest()
		
		payload = {
			'access_key': self._api_key,
			'nonce': str(uuid.uuid4()),
			'query_hash': query_hash,
			'query_hash_alg': 'SHA512',
		}
		
		jwt_token = jwt.encode(payload, self._secret_key)
		authorize_token = 'Bearer {}'.format(jwt_token)
		headers = {"Authorization": authorize_token}
		
		res = requests.post(url, params=query, headers=headers)
		
		return res.json()

	def create_market_buy_order(self, symbol, market, price):
		res = self._post_orders(symbol, market, 'bid', None, price, 'price')
		print(res)
		return res['uuid']
	
	def create_market_sell_order(self, symbol, market, volume):
		res = self._post_orders(symbol, market, 'ask', volume, None, 'market')
		
		return res['uuid']
	
	def _get_order(self, uuid_):
		url = 'https://api.upbit.com/v1/order'
		query = {
			'uuid': uuid_,
		}
		
		query_string = urlencode(query).encode()
		
		m = hashlib.sha512()
		m.update(query_string)
		query_hash = m.hexdigest()
		
		payload = {
			'access_key': self._api_key,
			'nonce': str(uuid.uuid4()),
			'query_hash': query_hash,
			'query_hash_alg': 'SHA512',
		}
		
		jwt_token = jwt.encode(payload, self._secret_key)
		authorize_token = 'Bearer {}'.format(jwt_token)
		headers = {"Authorization": authorize_token}
		
		res = requests.get(url, params=query, headers=headers)
		
		# https://docs.upbit.com/changelog/%EC%95%88%EB%82%B4-open-api-%EC%9E%90%EC%A3%BC%ED%95%98%EB%8A%94-%EB%AC%B8%EC%9D%98%EC%82%AC%ED%95%AD-%EC%8B%9C%EC%9E%A5%EA%B0%80-%EC%A3%BC%EB%AC%B8-%EA%B4%80%EB%A0%A8
		# 'state' can be 'wait', 'done', 'cancel'
		# 'cancel' can be shown in completed order, because there can remain dusts of krw.
		return res.json()
	
	def order_executed_volume(self, symbol, market, id_):
		res = self._get_order(id_)
		
		return float(res['executed_volume'])
	
	def is_order_fully_executed(self, symbol, market, id_):
		order_response = self._get_order(id_)
		
		if order_response['state'].lower() == 'done':
			return True
		elif order_response['state'].lower() == 'cancel':
			# Can't determine whether it's valid by remaining_volume,
			# because market-buy has no volume!!
			if order_response['ord_type'] == 'price' and float(order_response['executed_volume']) > 0:
				return True
	
	def wait_order(self, symbol, market, id_):
		order_response = self._get_order(id_)
		
		start_time_s = time.time()
		term_s = 1
		while True:
			if time.time() - start_time_s < term_s:
				continue
			
			if order_response['state'].lower() == 'done':
				return True
			elif order_response['state'].lower() == 'cancel':
				if self.is_order_fully_executed(symbol, market, id_):
					return True
				return False
				
			order_response = self._get_order(id_)
			start_time_s = time.time()
		
		return False
		
	def _delete_order(self, uuid_):
		url = 'https://api.upbit.com/v1/order'
		query = {
			'uuid': uuid_,
		}
		query_string = urlencode(query).encode()
		
		m = hashlib.sha512()
		m.update(query_string)
		query_hash = m.hexdigest()
		
		payload = {
			'access_key': self._api_key(),
			'nonce': str(uuid.uuid4()),
			'query_hash': query_hash,
			'query_hash_alg': 'SHA512',
		}
		
		jwt_token = jwt.encode(payload, self._secret_key())
		authorize_token = 'Bearer {}'.format(jwt_token)
		headers = {"Authorization": authorize_token}
		
		res = requests.delete(url, params=query, headers=headers)
		
		return res.json()
	
	def cancel_order(self, symbol, market, id_):
		return self._delete_order(id_)

	def price_filter(self, symbol, market, price):
		def floor(val, unit):
			return int(val / unit) * unit
		
		if 2000000 <= price:
			return floor(price, 1000)
		elif 1000000 <= price:
			return floor(price, 500)
		elif 500000 <= price:
			return floor(price, 100)
		elif 100000 <= price:
			return floor(price, 50)
		elif 10000 <= price:
			return floor(price, 10)
		elif 1000 <= price:
			return floor(price, 5)
		elif 100 <= price:
			return floor(price, 1)
		elif 10 <= price:
			return floor(price, 0.1)
		elif 1 <= price:
			return floor(price, 0.01)
		elif 0.1 <= price:
			return floor(price, 0.001)
		return floor(price, 0.0001)
		
	def quantity_filter(self, symbol, market, quantity, is_market=None):
		step_size = 0.0000001
		
		quantity = int(quantity / step_size) * step_size
		
		return quantity
import requests

from config import Config

class Telegram:
	GET_UPDATES_BASE_URL = 'https://api.telegram.org/bot{}/getUpdates'
	SEND_MESSAGE_BASE_URL = 'https://api.telegram.org/bot{}/sendMessage'
	
	LINE_BREAK = chr(10)
	
	@classmethod
	def args_to_message(cls, args):
		message = ''
		
		for arg in args:
			message = message + cls.LINE_BREAK + str(arg)
		
		return message
	
	@classmethod
	def send_message(cls, message):
		token = Config.load_config()['telegram']['token']
		chat_id = Config.load_config()['telegram']['chat id']
		
		send_message_url = cls.SEND_MESSAGE_BASE_URL.format(token)
		requests.get(send_message_url, params={'chat_id': chat_id, 'text': message, 'parse_mode': 'html'})
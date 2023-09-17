import logging, traceback
from flask import session
log = logging.getLogger('crdt')

def msg(string):
	return { 'message': string }

def route_shielded(func):
	def wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except ValueError as err:
			if str(err):
				log.error(f'Error in {func.__name__}: {traceback.format_exc()}')
			return msg(str(err)), 400
		except Exception as err:
			log.error(f'Error in {func.__name__}: {traceback.format_exc()}')
			return msg(f'Error in {func.__name__}, {str(err)}'), 500
	wrapper.__name__ = func.__name__
	return wrapper

def require_auth(func):
	def wrapper():
		if session.get('uid') is None: 
			return msg('Unauthorized'), 401
		return func()
	wrapper.__name__ = func.__name__
	return wrapper

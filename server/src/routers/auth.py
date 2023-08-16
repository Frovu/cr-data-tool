from routers.utils import route_shielded, require_auth
from flask import Blueprint, request, session
from server import bcrypt
from database import pool
import logging, os

log = logging.getLogger('crdt')
bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def init():
	with pool.connection() as conn:
		conn.execute('''CREATE TABLE IF NOT EXISTS users (
			uid SERIAL PRIMARY KEY,
			login TEXT UNIQUE,
			password TEXT NOT NULL,
			last_login TIMESTAMPTZ)''')
		exists = conn.execute('SELECT * FROM users WHERE login = \'admin\'').fetchone()
		if not exists:
			log.info('AUTH: Creating admin account')
			password = os.environ.get('ADMIN_PASSWORD')
			if not password:
				log.error('AUTH: please export ADMIN_PASSWORD')
				os._exit(1)
			pwd = bcrypt.generate_password_hash(password, rounds=10).decode()
			conn.execute('INSERT INTO users(login, password) VALUES (%s, %s)', ['admin', pwd])
init()

@bp.route('', methods=['POST'])
@route_shielded
def login():
	login = request.json.get('login')
	passw = request.json.get('password')
	if not login or not passw:
		return {}, 400
	with pool.connection() as conn:
		res = conn.execute('SELECT uid, login, password FROM users WHERE login = %s', [login]).fetchone()
		if not res: return {}, 404
		uid, uname, pwd = res
		if not bcrypt.check_password_hash(pwd.encode(), passw):
			return {}, 401
		conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE login = %s', [login])
	session['uid'] = uid
	session['uname'] = uname
	log.info(f'AUTH: user authorized: {login}')
	return { 'login': uname }

@bp.route('', methods=['GET'])
@route_shielded
def get_user():
	return { 'login': session.get('uname') }

@bp.route('/logout', methods=['POST'])
@route_shielded
def logout():
	uname = session.get('uname')
	if uname:
		session['uid'] = None
		session['uname'] = None
		log.info(f'AUTH: user logged out: {uname}')
	return { 'logout': uname }
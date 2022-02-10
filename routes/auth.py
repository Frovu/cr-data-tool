from flask import Blueprint, request, session
from server import bcrypt
import logging
from core import permissions
pg_conn = permissions.pg_conn

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('', methods=['POST'])
def register():
    try:
        login = request.values.get('login')
        passw = request.values.get('password')
        if not login or not passw:
            return {}, 400
        with pg_conn.cursor() as cursor:
            cursor.execute('SELECT login FROM users WHERE login = %s', [login])
            exists = cursor.fetchall()
            if exists:
                return { 'error': 'user exists' }, 409
            hash = bcrypt.generate_password_hash(passw, rounds=10).decode()
            cursor.execute('INSERT INTO users(login, password) VALUES (%s, %s)', [login, hash])
            pg_conn.commit()
        logging.info(f'AUTH: user registered: {login}')
        return { 'registered': login }
    except Exception as e:
        logging.error(f'ERROR: auth.register: {e}')
        return {}, 500

@bp.route('/login', methods=['POST'])
def login():
    try:
        login = request.values.get('login')
        passw = request.values.get('password')
        if not login or not passw:
            return {}, 400
        with pg_conn.cursor() as cursor:
            cursor.execute('SELECT uid, login, password FROM users WHERE login = %s', [login])
            res = cursor.fetchall()
        if not res: return {}, 404
        uid, uname, hash = res[0]
        if not bcrypt.check_password_hash(hash.encode(), passw):
            return {}, 401
        with pg_conn.cursor() as cursor:
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE login = %s', [login])
            pg_conn.commit()
        session['uid'] = uid
        session['uname'] = uname
        logging.info(f'AUTH: user authorized: {login}')
        return { 'login': uname, 'permissions': permissions.list() }
    except Exception as e:
        logging.error(f'ERROR: auth.login: {e}')
        return {}, 500

@bp.route('/login')
def check_login():
    return { 'login': session.get('uname'), 'permissions': permissions.list() }

@bp.route('/logout')
def logout():
    uname = session.get('uname')
    if uname:
        session['uid'] = None
        session['uname'] = None
        logging.info(f'AUTH: user logged out: {uname}')
    return { 'logout': uname }

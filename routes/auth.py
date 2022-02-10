from flask import Blueprint, request, session
from server import bcrypt
import logging
from modules import permissions
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
            cursor.execute('SELECT login FROM users WHERE login = $1', login)
            exists = cursor.fetchall()
            print(exists)
            if exists:
                return {}, 409
            hash = bcrypt.generate_password_hash(passw)
            cursor.execute('INSERT INTO users(login, password) VALUES ($1, $2)', login, hash)
            pg_conn.commit()
        logging.info(f'AUTH: user registered: {login}')
        return { 'registered': uname }
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
            cursor.execute('SELECT uid, login, password FROM users WHERE login = $1', login)
            res = cursor.fetchall()
        if not res: return {}, 404
        uid, uname, hash = res
        if not bcrypt.check_password_hash(hash, passw):
            return {}, 401
        session['uid'] = uid
        session['uname'] = uname
        logging.info(f'AUTH: user authorized: {login}')
        return { 'authorized': uname }
    except Exception as e:
        logging.error(f'ERROR: auth.register: {e}')
        return {}, 500

@bp.route('/login')
def check_login():
    uname = session.get('uname')
    return { 'login': uname }

@bp.route('/logout')
def logout():
    uname = session.get('uname')
    if uname:
        session['uid'] = None
        session['uname'] = None
        logging.info(f'AUTH: user logged out: {uname}')
    return { 'logout': uname }

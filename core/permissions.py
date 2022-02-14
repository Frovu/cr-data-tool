from flask import session, request
import logging
import os
import psycopg2

pg_conn = psycopg2.connect(
    dbname = 'cr_sys',
    user = 'crdt',
    password = os.environ.get("SYS_DB_PASS"),
    host = os.environ.get("SYS_DB_HOST")
)

ALLOWED_TYPES = [
    'USE_APPLICATION',
    'DELETE_DATA'
]

with pg_conn.cursor() as cursor:
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS users (
    uid SERIAL PRIMARY KEY, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login TIMESTAMP,
    login TEXT, password TEXT)''')
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS permissions (
    uid INTEGER NOT NULL, flag TEXT NOT NULL, target TEXT)''')
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS action_log (
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, uid INTEGER, type TEXT NOT NULL, target TEXT, details TEXT)''')
    pg_conn.commit()

def _check(uid, flag, target_required):
    with pg_conn.cursor() as cursor:
        cursor.execute('SELECT target FROM permissions WHERE uid = %s AND flag = %s', [ uid, flag ])
        targets = [r[0] for r in cursor.fetchall()]
    if target_required:
        return 'OVERRIDE' in targets or target_required in targets
    return len(targets) > 0

def require(flag, target=None):
    # if not target and flag == "manage_station"
    def decorator(func):
        def wrapper():
            uid = session.get("uid", None)
            if not uid:
                return { "error": "Unauthorized" }, 401
            if not _check(uid, flag, target):
                return { "error": "Forbidden" }, 403
            return func()
        return wrapper
    return decorator

def list(uid=None):
    uid = uid or session.get("uid", None)
    if not uid: return None;
    with pg_conn.cursor() as cursor:
        cursor.execute('SELECT flag, target FROM permissions WHERE uid = %s', [ uid ])
        rows = cursor.fetchall()
    perms = dict()
    for row in rows:
        flag = row[0]
        if (perms.get(flag)):
            perms[flag].append(row[1])
        else:
            perms[flag] = [ row[1] ]
    return perms

def log_action(type, target=None, details=None):
    uid = session.get("uid", None)
    with pg_conn.cursor() as cursor:
        cursor.execute('INSERT INTO action_log(uid, type, target, details) VALUES (%s, %s, %s, %s)',
            [ uid, type, target, details ])
        pg_conn.commit()
    tgt = ('->'+target) if target else ''
    dtls = ('('+details+')') if details else ''
    logging.info(f"USER[{session.get('uname') or 'anon'}] {type}{tgt} {dtls}")

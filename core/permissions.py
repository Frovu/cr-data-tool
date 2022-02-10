from flask import session, request
import os
import psycopg2

pg_conn = psycopg2.connect(
    dbname = 'cr_sys',
    user = 'crdt',
    password = os.environ.get("SYS_DB_PASS"),
    host = os.environ.get("SYS_DB_HOST")
)

with pg_conn.cursor() as cursor:
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS users (
    uid SERIAL PRIMARY KEY, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login TIMESTAMP,
    login TEXT, password TEXT)''')
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS permissions (
    uid INTEGER NOT NULL, flag TEXT NOT NULL, target TEXT)''')
    pg_conn.commit()

def check(uid, flag, target_required):
    with pg_conn.cursor() as cursor:
        cursor.execute('SELECT target FROM permissions WHERE uid = %s AND flag = %s', [ uid, flag ])
        targets = [r[0] for r in cursor.fetchall()]
    print(targets)
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
            if not check(uid, flag, target):
                return { "error": "Forbidden" }, 403
            func()
        return wrapper
    return decorator

from flask import session
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

def check_uid(uid, flag):
    pass

def check(flag):
    uid = session.get("uid", False)
    return uid and check_uid(uid, flag)

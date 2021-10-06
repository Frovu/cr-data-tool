import data_source.muones.obtain_data as parser

import psycopg2
import psycopg2.extras
pg_conn = psycopg2.connect(
    dbname = os.environ.get("MUON_DB_NAME"),
    user = os.environ.get("MUON_DB_USER"),
    password = os.environ.get("MUON_DB_PASS"),
    host = os.environ.get("MUON_DB_HOST")
)

FIELDS = [
    'n_v_raw',
    'n_v_pc',
    'n_v_tc',
    'pressure',
    'T_m'
]

def _table_name(station, period):
    per = f'{period // 3600}h' if period > 3600 and period % 3600 == 0 else f'{period}s'
    return f'proc_{station}_{per}'

def _create_if_not_exists(table_name):
    with pg_conn.cursor() as cursor:
        query = f'''CREATE TABLE IF NOT EXISTS {table_name} (
        time TIMESTAMP NOT NULL PRIMARY KEY,
        {", ".join([f"{f} REAL" for f in FIELDS])})'''
        cursor.execute(query)
        pg_conn.commit()

def station(lat, lon):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT name FROM stations WHERE round(lat::numeric,2) = %s AND round(lon::numeric,2) = %s', [round(lat, 2), round(lon, 2)])
        result = cursor.fetchall()
        return result[0][0] if result else None

def coordinates(station):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT lat, lon FROM stations WHERE name = %s', [station])
        result = cursor.fetchall()
        return result[0] if result else None

def analyze_integrity(station, dt_from, dt_to, period, fields=FIELDS):
    return False

def fill_raw(station, dt_from, dt_to, period):
    parser.obtain(station, dt_from, dt_to, period)

def select(station, dt_from, dt_to, period):
    pass

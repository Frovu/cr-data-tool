import data_source.muones.obtain_data as parser
import logging

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
    'raw_acc_cnt',
    'n_v_pc',
    'n_v_tc',
    'n_v',
    'pressure',
    'T_m'
]

def integrity_query(t_from, t_to, period, table, test_column, time_column='time'):
    return f'''WITH RECURSIVE
input (t_from, t_to, t_interval) AS (
    VALUES (to_timestamp({t_from}), to_timestamp({t_to}), interval \'{period} seconds\')
), filled AS (
    SELECT
        ser.tm as time, {test_column}
    FROM
        (SELECT generate_series(t_from, t_to, t_interval) tm FROM input) ser
    LEFT JOIN {table}
        ON (ser.tm = {table}.{time_column})
    ORDER BY time
), rec AS (
    SELECT
        t_from AS gap_start, t_from-t_interval AS gap_end
    FROM input
    UNION
    SELECT
        gap_start,
        COALESCE((SELECT time-t_interval FROM filled
            WHERE {test_column} IS NOT NULL AND time > gap_start LIMIT 1),t_to) AS gap_end
    FROM (
        SELECT
            (SELECT time FROM filled WHERE {test_column} IS NULL AND time > gap_end LIMIT 1) AS gap_start
        FROM rec, input
        WHERE gap_end < t_to
    ) r, input )
SELECT gap_start, gap_end FROM rec WHERE gap_end >= gap_start;'''
# TODO: EXTRACT(EPOCH FROM gap_start...)

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

def analyze_integrity(station, t_from, t_to, period, column='n_v'):
    table = _table_name(station, period)
    _create_if_not_exists(table)
    with pg_conn.cursor() as cursor:
        q = integrity_query(t_from, t_to, period, table, column)
        cursor.execute(q)
        return cursor.fetchall()

def select(station, t_from, t_to, period, columns=FIELDS):
    pass

def upsert(station, period, data, columns):
    if not len(data): return
    with pg_conn.cursor() as cursor:
        query = f'''INSERT INTO {_table_name(station, period)} (time, {", ".join(columns)}) VALUES %s
        ON CONFLICT (time) DO UPDATE SET ({", ".join(FIELDS)}) = ({", ".join([f"EXCLUDED.{f}" for f in FIELDS])})'''
        psycopg2.extras.execute_values (cursor, query, data, template=None)
        pg_conn.commit()
        logging.info(f'Upsert: {_table_name(station, period)}<-[{len(data)}] {columns}')

dt_strt = datetime(2021, 10, 5)
dt_end = datetime(2021, 10, 7)
for r in obtain('Moscow', dt_strt, dt_end):
    print(*r)

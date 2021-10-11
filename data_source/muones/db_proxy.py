import data_source.muones.obtain_data as parser
import logging
import os

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

def integrity_query(t_from, t_to, period, table, test_column, time_column='time', epoch=True):
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
SELECT {", ".join([f"EXTRACT(EPOCH FROM {f})::integer" if epoch else f for f in ["gap_start", "gap_end"]])}
 FROM rec WHERE gap_end >= gap_start;'''

def _table_name(station, period):
    per = f'{period // 3600}h' if period >= 3600 and period % 3600 == 0 else f'{period}s'
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

def analyze_integrity(station, t_from, t_to, period, columns='n_v'):
    # FIXME: some extra wacky hack to analyze across several columns without geting intervals
    if type(columns) is list:
        for col in columns:
            if analyze_integrity(station, t_from, t_to, period, col):
                return True
        return False

    table = _table_name(station, period)
    _create_if_not_exists(table)
    with pg_conn.cursor() as cursor:
        q = integrity_query(t_from, t_to, period, table, columns)
        cursor.execute(q)
        return cursor.fetchall()

def select(station, t_from, t_to, period, columns=FIELDS, include_time=True):
    with pg_conn.cursor() as cursor:
        q = f'''SELECT {"EXTRACT(EPOCH FROM time)," if include_time else ""}{",".join(columns)}
            FROM {_table_name(station, period)} WHERE time >= to_timestamp(%s) AND time <= to_timestamp(%s)'''
        cursor.execute(q, [t_from, t_to])
        return cursor.fetchall()

def upsert(station, period, data, columns, epoch=False):
    if not len(data): return
    with pg_conn.cursor() as cursor:
        query = f'''INSERT INTO {_table_name(station, period)} (time, {", ".join(columns)}) VALUES %s
        ON CONFLICT (time) DO UPDATE SET (time,{", ".join(columns)}) = ({", ".join([f"EXCLUDED.{f}" for f in ["time"]+columns])})'''
        psycopg2.extras.execute_values (cursor, query, data,
            template=f'(to_timestamp(%s),{",".join(["%s" for f in columns])})' if epoch else None)
        pg_conn.commit()
        logging.info(f'Upsert: {_table_name(station, period)} <-[{len(data)}] {",".join(columns)} from {data[0][0]}')

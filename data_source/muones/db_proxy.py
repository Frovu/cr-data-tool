from core.sql_queries import integrity_query
import logging
import os

import psycopg2
import psycopg2.extras
pg_conn = psycopg2.connect(
    dbname = os.environ.get("MUON_DB_NAME") or "cr_cr",
    user = os.environ.get("MUON_DB_USER") or "crdt",
    password = os.environ.get("MUON_DB_PASS"),
    host = os.environ.get("MUON_DB_HOST")
)

DATA_FIELDS = [
    'count_raw',
    'count_corr_p',
    'count_corr',
    'pressure',
    'T_m'
]

def _table_name(station, period):
    per = f'{period // 3600}h' if period >= 3600 and period % 3600 == 0 else f'{period}s'
    return f'muon_{station}_{per}'

def _create_if_not_exists(station, period):
    with pg_conn.cursor() as cursor:
        query = f'''CREATE TABLE IF NOT EXISTS {_table_name(station, period)} (
        time TIMESTAMP NOT NULL PRIMARY KEY,
        channel TEXT,
        raw_acc_cnt INTEGER DEFAULT 1,
        {", ".join([f"{f} REAL" for f in DATA_FIELDS])})'''
        cursor.execute(query)
        pg_conn.commit()

def stations():
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT name, lat, lon FROM stations')
        result = []
        for s in cursor.fetchall():
            result.append({'name': s[0], 'lat': float(s[1]), 'lon': float(s[2])})
        return result

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

def analyze_integrity(station, t_from, t_to, period, channel='V', columns='count_corr'):
    # FIXME: some extra wacky hack to analyze across several columns without geting intervals
    if type(columns) is list:
        for col in columns:
            if analyze_integrity(station, t_from, t_to, period, col):
                return True
        return False

    _create_if_not_exists(station, period)
    with pg_conn.cursor() as cursor:
        q = integrity_query(t_from, t_to, period, table, columns)
        cursor.execute(q)
        return cursor.fetchall()

def select(station, t_from, t_to, period, channel='V', columns=['count_corr'], include_time=True, order='time', where=''):
    with pg_conn.cursor() as cursor:
        q = f'''SELECT {"EXTRACT(EPOCH FROM time)," if include_time else ""}{",".join(columns)}
FROM {_table_name(station, period)} WHERE time >= to_timestamp(%s) AND time <= to_timestamp(%s)
{"AND "+where if where else ""} ORDER BY {order}'''
        cursor.execute(q, [t_from, t_to])
        return cursor.fetchall(), (['time']+columns) if include_time else columns

def upsert(station, period, channel, data, columns, epoch=False):
    if not len(data): return
    with pg_conn.cursor() as cursor:
        query = f'''INSERT INTO {_table_name(station, period)} (time, {", ".join(columns)}) VALUES %s
        ON CONFLICT (time) DO UPDATE SET (time,{", ".join(columns)}) = ({", ".join([f"EXCLUDED.{f}" for f in ["time"]+columns])})'''
        psycopg2.extras.execute_values (cursor, query, data,
            template=f'(to_timestamp(%s),{",".join(["%s" for f in columns])})' if epoch else None)
        pg_conn.commit()
        logging.info(f'Upsert: {_table_name(station, period)} <-[{len(data)}] {",".join(columns)} from {data[0][0]}')

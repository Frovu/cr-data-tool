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
        time TIMESTAMP NOT NULL,
        channel TEXT,
        raw_acc_cnt INTEGER DEFAULT 1,
        {", ".join([f"{f} REAL" for f in DATA_FIELDS])},
        UNIQUE (time, channel))'''
        cursor.execute(query)
        pg_conn.commit()

def stations():
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT name, lat, lon, (SELECT array_agg(channel_name) AS channels FROM muon_channels WHERE station_name = name) FROM muon_stations')
        result = []
        for s in cursor.fetchall():
            print
            result.append({'name': s[0], 'lat': float(s[1]), 'lon': float(s[2]), 'channels': s[3]})
        return result

def station(lat, lon):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT name FROM muon_stations WHERE round(lat::numeric,2) = %s AND round(lon::numeric,2) = %s', [round(lat, 2), round(lon, 2)])
        result = cursor.fetchall()
        return result[0][0] if result else None

def coordinates(station):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT lat, lon FROM muon_stations WHERE name = %s', [station])
        result = cursor.fetchall()
        return result[0] if result else None

def channel(station, channel):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT coef_pressure, coef_tm FROM muon_channels WHERE station_name = %s AND channel_name = %s', [station, channel])
        result = cursor.fetchall()
        return result[0] if result else None

def analyze_integrity(station, t_from, t_to, period, channel='V', columns='count_corr'):
    # FIXME: some extra wacky hack to analyze across several columns without geting intervals
    if type(columns) is list:
        for col in columns:
            if analyze_integrity(station, t_from, t_to, period, channel, col):
                return True
        return False

    _create_if_not_exists(station, period)
    with pg_conn.cursor() as cursor:
        q = integrity_query(t_from, t_to, period, _table_name(station, period),
            columns, where=f'channel = \'{channel}\'')
        cursor.execute(q)
        return cursor.fetchall()

def select(station, t_from, t_to, period, channel='V', columns=['count_corr'], include_time=True, order='time', where=''):
    with pg_conn.cursor() as cursor:
        q = f'''SELECT {"EXTRACT(EPOCH FROM time)," if include_time else ""}{",".join(columns)}
FROM {_table_name(station, period)} WHERE channel = %s AND time >= to_timestamp(%s) AND time <= to_timestamp(%s)
{"AND "+where if where else ""} ORDER BY {order}'''
        cursor.execute(q, [channel, t_from, t_to])
        return cursor.fetchall(), (['time']+columns) if include_time else columns

def upsert(station, period, channel, data, columns, epoch=False):
    if not len(data): return
    with pg_conn.cursor() as cursor:
        query = f'''INSERT INTO {_table_name(station, period)} (channel, {", ".join(columns)}) VALUES %s
        ON CONFLICT (time, channel) DO UPDATE SET ({", ".join(columns)}) = ({", ".join([f"EXCLUDED.{f}" for f in columns])})'''
        tl = f'(\'{channel}\',{"to_timestamp(%s)" if epoch else "%s"},{",".join(["%s" for f in columns[1:]])})'
        psycopg2.extras.execute_values (cursor, query, data, template=tl)
        pg_conn.commit()
        logging.info(f'Upsert: {_table_name(station, period)}/{channel} <-[{len(data)}] {",".join(columns[-2:])} from {data[0][0]}')

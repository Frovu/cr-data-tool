from core.sql_queries import integrity_query
import data_source.temperature_model.proxy as model_proxy
pg_conn = model_proxy.pg_conn
import psycopg2.extras
import numpy
import logging as log

FIELDS = ['t2', 't_indoors', 'pressure']

def _table_name(station_name):
    return f'local_{station_name}'

def _create_if_not_exists(table):
    with pg_conn.cursor() as cursor:
        query = f'''CREATE TABLE IF NOT EXISTS {table} (
        time TIMESTAMP NOT NULL PRIMARY KEY,
        integrity SMALLINT,
        {", ".join([f"{f} REAL" for f in FIELDS])})'''
        cursor.execute(query)
        pg_conn.commit()

def select_station(lat, lon):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT name FROM stations WHERE round(lat::numeric,2) = %s AND round(lon::numeric,2) = %s', [round(lat, 2), round(lon, 2)])
        result = cursor.fetchall()
        return result[0][0] if result else None

def analyze_integrity(station, t_from, t_to, period=3600):
    table = _table_name(station)
    _create_if_not_exists(table)
    with pg_conn.cursor() as cursor:
        q = integrity_query(t_from, t_to, period, table, 'integrity')
        cursor.execute(q)
        return cursor.fetchall()

def select(station, t_from, t_to, with_model=False):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT lat, lon FROM stations WHERE name = %s', [station])
        lat, lon = cursor.fetchall()[0]
    if with_model:
        fields = ['time', 'p_station', 't2', 't_mass_avg'] + [f't_{int(l)}mb' for l in model_proxy.LEVELS]
        query = f'''SELECT EXTRACT(EPOCH FROM m.time) AS time, l.pressure as p_station, l.t2 as t2, m.{model_proxy.T_M_COLUMN} as t_mass_avg,
        {", ".join([f'm.p_{int(l)} AS t_{int(l)}mb' for l in model_proxy.LEVELS])}
        FROM {model_proxy.table_name(lat, lon)} m FULL OUTER JOIN {_table_name(station)} l
        ON (m.time = l.time) WHERE m.time >= to_timestamp(%s) AND m.time <= to_timestamp(%s) ORDER BY m.time'''
    else:
        fields = ['time'] + FIELDS
        query =  f'''
        SELECT EXTRACT(EPOCH FROM time), {", ".join(FIELDS)} FROM {_table_name(station)} WHERE time >= to_timestamp(%s) AND time <= to_timestamp(%s) ORDER BY time'''
    with pg_conn.cursor() as cursor:
        cursor.execute(query, [t_from, t_to])
        rows = cursor.fetchall()
    return rows, fields

def insert(station, data, columns):
    if not len(data): return
    with pg_conn.cursor() as cursor:
        query = f'''INSERT INTO {_table_name(station)} (integrity,time,{", ".join(columns)}) VALUES %s
        ON CONFLICT (time) DO UPDATE SET (integrity,{", ".join(columns)}) = (1,{", ".join([f"EXCLUDED.{f}" for f in columns])})'''
        psycopg2.extras.execute_values (cursor, query, data, template=f'(1,to_timestamp(%s),{",".join(["%s" for f in columns])})')
        pg_conn.commit()
        log.info(f'aws.rmp: {station} <- [{len(data)}] from {data[0][0]}')

def fill_empty(station, t_from, t_to, period):
    with pg_conn.cursor() as cursor:
        q = f'''INSERT INTO {_table_name(station)} (time, integrity)
(SELECT t, 1 FROM generate_series(to_timestamp({t_from}), to_timestamp({t_to}), interval \'{period} s\') t)
ON CONFLICT (time) DO UPDATE SET integrity = 1'''
        cursor.execute(q)
        pg_conn.commit()
        log.info(f'aws.rmp: {station} <- [hopeless] {t_from}:{t_to}')

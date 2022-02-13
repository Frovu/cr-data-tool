import os
from datetime import datetime, timezone
import logging as log
from core.sql_queries import integrity_query
import numpy
import psycopg2
import psycopg2.extras
from psycopg2.extensions import register_adapter, AsIs
def addapt_float32(numpy_float32):
    return AsIs(numpy_float32)
register_adapter(numpy.float32, addapt_float32)

pg_conn = psycopg2.connect(
    dbname = os.environ.get("METEO_DB_NAME") or "cr_meteo",
    user = os.environ.get("METEO_DB_USER") or "crdt",
    password = os.environ.get("METEO_DB_PASS"),
    host = os.environ.get("METEO_DB_HOST")
)

_INSERT_CHUNK_SIZE = 100
LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20, 10]
FC_COLUMN = 'forecast'
T_M_COLUMN = 'mass_average'
LEVELS_COLUMNS = [f'p_{int(l)}' for l in LEVELS]

stations = []
def _fetch_existing():
    with pg_conn.cursor() as cursor:
        cursor.execute('SELECT lat, lon, name FROM stations')
        log.info(f"TEMPERATURE: Starting with {cursor.rowcount} stations")
        for row in cursor.fetchall():
            stations.append({'name': row[2], 'lat': row[0], 'lon': row[1]})
            _create_if_not_exists(row[0], row[1])

def table_name(lat, lon):
    return f"ncep_proc_{int(lat*100)}_{'N' if lat>0 else 'S'}_{int(lon*100)}_{'E' if lat>0 else 'W'}"

def _create_if_not_exists(lat, lon):
    with pg_conn.cursor() as cursor:
        query = f'''CREATE TABLE IF NOT EXISTS {table_name(lat, lon)} (
time TIMESTAMP NOT NULL PRIMARY KEY,
forecast TIMESTAMP,
{T_M_COLUMN} REAL,
{", ".join([f"{l} REAL NOT NULL" for l in LEVELS_COLUMNS])})'''
        cursor.execute(query)
        pg_conn.commit()
_fetch_existing()

def get_station(lat, lon):
    return next((x for x in stations if (x.get('lat') == lat and x.get('lon') == lon)), None)

def get_stations():
    return stations

# return list of time period turples for which data is missing
def analyze_integrity(lat, lon, t_from, t_to, fc_age='2 days', model_lag='4 days'):
    station = get_station(lat, lon)
    if not station:
        return False
    q = integrity_query(t_from, t_to, 3600, table_name(lat, lon), LEVELS_COLUMNS[0], return_epoch=True,
        bad_cond_columns=['forecast'],
        bad_condition=f'''forecast IS NOT NULL AND
(time < \'now\'::timestamp - interval \'{model_lag}\' OR
(time - forecast > interval \'8 h\' AND \'now\'::timestamp - forecast > interval \'{fc_age}\'))''')
    with pg_conn.cursor() as cursor:
        cursor.execute(q)
        return cursor.fetchall()

def select(lat, lon, t_from, t_to, only=[]):
    result = []
    fields = only or ([T_M_COLUMN] + LEVELS_COLUMNS)
    ret_fields = only or (['t_mass_avg'] + [f't_{int(l)}mb' for l in LEVELS])
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT EXTRACT(EPOCH FROM time)::integer, {",".join(fields)} FROM {table_name(lat, lon)} ' +
            'WHERE time >= to_timestamp(%s) AND time <= to_timestamp(%s) ORDER BY time', [t_from, t_to])
        return cursor.fetchall(), ['time'] + ret_fields

def insert(lat, lon, data, forecast=False):
    if not len(data): return
    log.info(f'TEMPERATURE: Insert: {table_name(lat, lon)} <-[{len(data)}] {data[0][0]}:{data[-1][0]}')
    cols = ['time', 'forecast', T_M_COLUMN] + LEVELS_COLUMNS
    query = f'INSERT INTO {table_name(lat, lon)}({",".join(cols)}) VALUES %s ON CONFLICT (time) DO UPDATE SET ' + ', '.join([f'{col} = EXCLUDED.{col}' for col in [FC_COLUMN, T_M_COLUMN] + LEVELS_COLUMNS])
    with pg_conn.cursor() as cursor:
        psycopg2.extras.execute_values (cursor, query, data,
            template='(to_timestamp(%s)'+(',to_timestamp(%s)' if forecast else ',NULL')+
            ''.join([',%s' for i in range(data.shape[1]-(2 if forecast else 1))])+')')
        pg_conn.commit()

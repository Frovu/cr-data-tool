import os
from datetime import datetime, timezone
import logging as log
from data_source.muones.db_proxy import integrity_query
import numpy
import psycopg2
import psycopg2.extras
from psycopg2.extensions import register_adapter, AsIs
def addapt_float32(numpy_float32):
    return AsIs(numpy_float32)
register_adapter(numpy.float32, addapt_float32)

pg_conn = psycopg2.connect(
    dbname = os.environ.get("METEO_DB_NAME"),
    user = os.environ.get("METEO_DB_USER"),
    password = os.environ.get("METEO_DB_PASS"),
    host = os.environ.get("METEO_DB_HOST")
)

_INSERT_CHUNK_SIZE = 100
LEVELS = [1000.0, 925.0, 850.0, 700.0, 600.0, 500.0, 400.0, 300.0, 250.0, 200.0,
 150.0, 100.0, 70.0, 50.0, 30.0, 20.0, 10.0]

stations = []
def _fetch_existing():
    with pg_conn.cursor() as cursor:
        cursor.execute('SELECT lat, lon, name FROM stations')
        log.info(f"Temperature model: starting with {cursor.rowcount} stations")
        for row in cursor.fetchall():
            stations.append({'name': row[2], 'lat': row[0], 'lon': row[1]})
            _create_if_not_exists(row[0], row[1])

def table_name(lat, lon):
    return f"ncep_proc_{int(lat*100)}_{'N' if lat>0 else 'S'}_{int(lon*100)}_{'E' if lat>0 else 'W'}"
def _create_if_not_exists(lat, lon):
    with pg_conn.cursor() as cursor:
        query = f'''CREATE TABLE IF NOT EXISTS {table_name(lat, lon)} (
        time TIMESTAMP NOT NULL PRIMARY KEY,
        {", ".join([f"p_{int(l)} REAL NOT NULL" for l in LEVELS])})'''
        cursor.execute(query)
        pg_conn.commit()
_fetch_existing()

def get_station(lat, lon):
    return next((x for x in stations if (x.get('lat') == lat and x.get('lon') == lon)), None)

def get_stations():
    return stations

# return list of time period turples for which data is missing
def analyze_integrity(lat, lon, dt_from, dt_to):
    station = get_station(lat, lon)
    if not station:
        return False
    log.debug(f'Querying station \'{station.get("name")}\' from {dt_from} to {dt_to}')
    t_from = dt_from.replace(tzinfo=timezone.utc).timestamp()
    t_to = dt_to.replace(tzinfo=timezone.utc).timestamp()
    q = integrity_query(t_from, t_to, 3600, table_name(lat, lon), f'p_{int(LEVELS[0])}', epoch=False)
    with pg_conn.cursor() as cursor:
        cursor.execute(q)
        return cursor.fetchall()

def select(lat, lon, start_time, end_time):
    result = []
    fields = [f't_{int(l)}mb' for l in LEVELS]
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT EXTRACT(EPOCH FROM time), {",".join([f"p_{int(l)}" for l in LEVELS])} ' +
            'FROM {table_name(lat, lon)} WHERE time >= %s AND time <= %s ORDER BY time', [start_time, end_time])
        return cursor.fetchall(), ['time'] + fields

def insert(data, lat, lon):
    if not data: return
    log.info(f'Inserting {len(data)} lines from {data[0][0]} to {data[-1][0]}')
    with pg_conn.cursor() as cursor:
        query = f'INSERT INTO {table_name(lat, lon)} VALUES %s ON CONFLICT (time) DO NOTHING'
        psycopg2.extras.execute_values (cursor, query, data, template=None, page_size=100)
        pg_conn.commit()

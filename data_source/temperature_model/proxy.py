import os
from datetime import datetime, timedelta, time
import logging as log

import numpy
import psycopg2
import psycopg2.extras
from psycopg2.extensions import register_adapter, AsIs
def addapt_float32(numpy_float32):
    return AsIs(numpy_float32)
register_adapter(numpy.float32, addapt_float32)

pg_conn = psycopg2.connect(
    dbname = os.environ.get("NCEP_DB_NAME"),
    user = os.environ.get("NCEP_DB_USER"),
    password = os.environ.get("NCEP_DB_PASS"),
    host = os.environ.get("NCEP_DB_HOST")
)

_INSERT_CHUNK_SIZE = 100
LEVELS = [1000.0, 925.0, 850.0, 700.0, 600.0, 500.0, 400.0, 300.0, 250.0, 200.0,
 150.0, 100.0, 70.0, 50.0, 30.0, 20.0, 10.0]

stations = []
def _fetch_existing():
    with pg_conn.cursor() as cursor:
        cursor.execute('SELECT lat, lon, name FROM index')
        log.info(f"Starting with {cursor.rowcount} stations")
        for row in cursor.fetchall():
            stations.append({'name': row[2], 'lat': row[0], 'lon': row[1]})
            _create_if_not_exists(row[0], row[1])

def _table_name(lat, lon):
    return f"proc_{int(lat*100)}_{'N' if lat>0 else 'S'}_{int(lon*100)}_{'E' if lat>0 else 'W'}"
def _create_if_not_exists(lat, lon):
    with pg_conn.cursor() as cursor:
        query = f'''CREATE TABLE IF NOT EXISTS {_table_name(lat, lon)} (
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
# this could be done by complex SQL query probably
def analyze_integrity(lat, lon, start_time, end_time):
    station = get_station(lat, lon)
    if not station:
        return False
    log.info(f'Querying station \'{station.get("name")}\' from {start_time} to {end_time}')
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT time FROM {_table_name(lat, lon)} ' +
            'WHERE time >= %s AND time <= %s ORDER BY time', [start_time, end_time])
        rows = cursor.fetchall()

    missing = []
    inc = timedelta(hours=1)
    # round start and end to 6h periods
    start = datetime.combine(start_time, time(start_time.hour))
    if start_time.minute+start_time.second > 0: start += inc
    end = datetime.combine(end_time, time(end_time.hour))

    cur = start # next timestamp we want to see
    for row in rows:
        if row[0] > cur: # if something skipped account missing interval
            missing.append((cur, row[0] - inc))
            cur = row[0]
        cur += inc
    if cur <= end: # if end not reached (cur==end means last is missing)
        missing.append((cur, end))
    return missing

def select(lat, lon, start_time, end_time):
    result = []
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT * FROM {_table_name(lat, lon)} ' +
            'WHERE time >= %s AND time <= %s ORDER BY time', [start_time, end_time])
        for row in cursor.fetchall():
            result.append([row[0].timestamp()]+list(row[1:]))
    return result

def insert(data, lat, lon):
    if not data: return
    log.debug(f'Inserting {len(data)} lines from {data[0][0]} to {data[-1][0]}')
    with pg_conn.cursor() as cursor:
        query = f'INSERT INTO {_table_name(lat, lon)} VALUES %s ON CONFLICT (time) DO NOTHING'
        psycopg2.extras.execute_values (cursor, query, data, template=None, page_size=100)
        pg_conn.commit()

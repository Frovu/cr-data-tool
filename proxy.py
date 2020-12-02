import os
import numpy as np
from netCDF4 import Dataset, num2date, date2index
from datetime import datetime, timedelta, time
import logging as log
log.basicConfig(
    format='%(asctime)s/%(levelname)s: %(message)s', level=log.INFO,
    handlers=[
        log.FileHandler('log.log', mode='a'),
        log.StreamHandler()
    ]
)

import psycopg2
pg_conn = psycopg2.connect(
    dbname = os.environ.get("DB_NAME"),
    user = os.environ.get("DB_USER"),
    password = os.environ.get("DB_PASS"),
    host = os.environ.get("DB_HOST")
)
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
        time TIMESTAMP NOT NULL,
        {", ".join([f"p_{int(l)} REAL NOT NULL" for l in LEVELS])})'''
        cursor.execute(query)
        pg_conn.commit()

def _extract(filename, lat, lon, start_time, end_time):
    data = Dataset(filename, 'r')
    print(data.title)
    print(", ".join([str(i) for i in data.variables["level"][:]]))
    assert "NMC reanalysis" in data.title
    air = data.variables["air"]
    times = data.variables["time"]
    print(end_time in num2date(times[:], units=times.units))
    lat_idx = np.where(data.variables["lat"][:] == lat)
    lon_idx = np.where(data.variables["lon"][:] == lon)
    start_idx = date2index(start_time, times)
    end_idx = date2index(end_time, times)
    print(f"lat={lat} lon={lon} from={start_time.date()}({start_idx}) to={end_time.date()}({end_idx})")
    for level_i, level in enumerate(data.variables["level"][:]):
        line = [a[level_i][lat][lon] for a in air[start_idx:end_idx]]
        print(f'{level}:\t{"  ".join([str("%.1f" % i) for i in line])}')

# return list of time period turples for which data is missing
def _analyze_integrity(lat, lon, start_time, end_time):
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

def _select(lat, lon, start_time, end_time):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT time FROM {_table_name(lat, lon)} ' +
            'WHERE time >= %s AND time <= %s ORDER BY time', [start_time, end_time])
        result = []
        for row in cursor.fetchall():
            result.append(row)

def query(lat, lon, start_time, end_time):
    station = next((x for x in stations if (x.get('lat') == lat and x.get('lon') == lon)), None)
    if not station:
        return False
    log.info(f'Querying station \'{station.get("name")}\' from {start_time} to {end_time}')
    missing_intervals = _analyze_integrity(lat, lon, start_time, end_time)
    if len(missing_intervals):
        print("Missing intervals:")
        for i in missing_intervals:
            print(f"\tfrom {i[0].ctime()}\n\t\tto {i[1].ctime()}")
    else:
        _select

_fetch_existing()
query(55.47, 37.32 ,
    datetime.strptime('2020-01-01', '%Y-%m-%d'),
    datetime.strptime('2020-01-02', '%Y-%m-%d'))

import numpy as np
import os
from netCDF4 import Dataset, num2date, date2index
from datetime import datetime
import psycopg2
pg_conn = psycopg2.connect(
    dbname = os.environ.get("DB_NAME"),
    user = os.environ.get("DB_USER"),
    password = os.environ.get("DB_PASS"),
    host = os.environ.get("DB_HOST")
)
LEVELS = [1000.0, 925.0, 850.0, 700.0, 600.0, 500.0, 400.0, 300.0, 250.0, 200.0,
 150.0, 100.0, 70.0, 50.0, 30.0, 20.0, 10.0]

def _table_name(lat, lon):
    return f"proc_lat_{int(lat*100)}_lon_{int(lon*100)}"

def _create_if_not_exists(lat, lon):
    with pg_conn.cursor() as cursor:
        query = f'''CREATE TABLE IF NOT EXISTS {_table_name(lat, lon)} (
        time TIMESTAMP NOT NULL,
        {", ".join([f"p_{int(l)} REAL NOT NULL" for l in LEVELS])})'''
        print(query)
        cursor.execute(query)

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
def _select_and_analyze(lat, lon, start_time, end_time):
    _create_if_not_exists(lat, lon)
    with pg_conn.cursor() as cursor:
        cursor.execute('')
        for row in cursor.fetchall():
            print(row)

def query(lat, lon, start_time, end_time):
    data = _select_and_analyze(lat, lon, start_time, end_time)


# './tmp/air.nc/air.2020.nc'
#_extract('./tmp/air.nc/air.2019.nc', 0, 0,
#    datetime.strptime('2020-01-01', '%Y-%m-%d'),
#    datetime.strptime('2020-01-02', '%Y-%m-%d'))
query(0,0,0,0)

print()

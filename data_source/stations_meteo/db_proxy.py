import data_source.temperature_model.proxy as model_proxy
pg_conn = model_proxy.pg_conn
import psycopg2.extras
import numpy

FIELDS = ['t2', 't_indoors', 'pressure']

def _table_name(station_name):
    return f'local_{station_name}'

def _create_if_not_exists(station_name):
    with pg_conn.cursor() as cursor:
        query = f'''CREATE TABLE IF NOT EXISTS {_table_name(station_name)} (
        time TIMESTAMP NOT NULL PRIMARY KEY,
        {", ".join([f"{f} REAL" for f in FIELDS])})'''
        cursor.execute(query)
        pg_conn.commit()

def select_station(lat, lon):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT name FROM stations WHERE round(lat::numeric,2) = %s AND round(lon::numeric,2) = %s', [round(lat, 2), round(lon, 2)])
        result = cursor.fetchall()
        return result[0][0] if result else None

# TODO: use complex sql query to return pairs of edges of missing intervals
def analyze_integrity(station, dt_from, dt_to, period=3600):
    delta = dt_to - dt_from
    required_count = delta.days*(86400//period) + delta.seconds//period
    _create_if_not_exists(station)
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT count(*) FROM {_table_name(station)} WHERE time >= %s AND time <= %s', [dt_from, dt_to])
        count = cursor.fetchall()[0][0]
        return count >= required_count

def select(station, dt_from, dt_to, with_model=False):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT lat, lon FROM stations WHERE name = %s', [station])
        lat, lon = cursor.fetchall()[0]
    if with_model:
        fields = ['time', 'p_station', 't2'] + [f't_{int(l)}mb' for l in model_proxy.LEVELS]
        query = f'''SELECT EXTRACT(EPOCH FROM m.time) AS time, l.pressure as p_station, l.t2 as t2,
        {", ".join([f'm.p_{int(l)} AS t_{int(l)}mb' for l in model_proxy.LEVELS])}
        FROM {model_proxy.table_name(lat, lon)} m FULL OUTER JOIN {_table_name(station)} l
        ON (m.time = l.time) WHERE m.time >= %s AND m.time <= %s ORDER BY m.time'''
    else:
        fields = ['time'] + FIELDS
        query =  f'''
        SELECT EXTRACT(EPOCH FROM time), {", ".join(FIELDS)} FROM {_table_name(station)} WHERE time >= %s AND time <= %s ORDER BY time'''
    with pg_conn.cursor() as cursor:
        cursor.execute(query, [dt_from, dt_to])
        rows = cursor.fetchall()
    # for i in range(len(rows)):
    #     rows[i][0] = rows[i][0].timestamp()
    return rows, fields

def insert(data, columns, station):
    if not len(data): return
    # _create_if_not_exists(station) # technically useless here since analyze_integrity() is always called beforehand
    with pg_conn.cursor() as cursor:
        query = f'''INSERT INTO {_table_name(station)} (time, {", ".join(columns)}) VALUES %s
        ON CONFLICT (time) DO UPDATE SET ({", ".join(FIELDS)}) = ({", ".join([f"EXCLUDED.{f}" for f in FIELDS])})'''
        psycopg2.extras.execute_values (cursor, query, data, template=None, page_size=100)
        pg_conn.commit()

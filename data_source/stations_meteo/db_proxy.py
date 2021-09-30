
from data_source.temperature_model.proxy import pg_conn
import psycopg2.extras

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

# TODO: use complex sql query to return pairs of edges of missing intervals
def analyze_integrity(dt_from, dt_to):
    return False

def select_station(lat, lon):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT name FROM stations WHERE round(lat::numeric,2) = %s AND round(lon::numeric,2) = %s', [round(lat, 2), round(lon, 2)])
        result = cursor.fetchall()
        return result[0][0] if result else None

def select(station, dt_from, dt_to, with_model=False):
    pass

def insert(data, columns, station):
    if not len(data): return
    _create_if_not_exists(station)
    with pg_conn.cursor() as cursor:
        query = f'''INSERT INTO {_table_name(station)} (time, {", ".join(columns)}) VALUES %s
        ON CONFLICT (time) DO UPDATE SET ({", ".join(FIELDS)}) = ({", ".join([f"EXCLUDED.{f}" for f in FIELDS])})'''
        psycopg2.extras.execute_values (cursor, query, data, template=None, page_size=100)
        pg_conn.commit()

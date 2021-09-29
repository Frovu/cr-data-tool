
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

def insert(data, station):
    if not data: return
    log.debug(f'{_table_name(station)} <- [{len(data)}] from {data[0][0]} to {data[-1][0]}')
    with pg_conn.cursor() as cursor:
        query = f'INSERT INTO {_table_name(station)} VALUES %s ON CONFLICT (time) DO NOTHING'
        psycopg2.extras.execute_values (cursor, query, data, template=None, page_size=100)
        pg_conn.commit()

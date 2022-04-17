from data_source.muon.proxy import pg_conn
from core.sql_queries import integrity_query
from concurrent.futures import ThreadPoolExecutor
import os, logging, pymysql.cursors, numpy
import psycopg2, psycopg2.extras
from datetime import datetime

PERIOD = 3600
nmdb_conn = None

with pg_conn.cursor() as cursor:
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS neutron_counts (
    time TIMESTAMP NOT NULL,
    station TEXT NOT NULL,
    uncorrected REAL,
    corrected REAL,
    pressure REAL,
    UNIQUE(time, station))''')
    pg_conn.commit()

def _connect_nmdb():
    if not nmdb_conn:
        logging.info('Connecting to NMDB')
        nmdb_conn = pymysql.connect(
            host=os.environ.get("NMDB_HOST"),
            port=os.environ.get("NMDB_PORT") or 0,
            user=os.environ.get("NMDB_USER"),
            password=os.environ.get("NMDB_PASS"),
            database='nmdb')

def _obtain_nmdb(interval, station, pg_cursor):
    _connect_nmdb()
    dt_interval = [datetime.utcfromtimestamp(t) for t in dt_interval]
    with nmdb_conn.cursor() as cursor:
        cursor.execute(f'''SELECT start_date_time dt, uncorrected, corr_for_efficiency, pressure
            FROM {station}_1h WHERE dt >= %s AND dt <= %s''', dt_interval)
        data = cursor.fetchall()
    logging.info(f'Neutron: obtain nmdb [{len(data)}] {dt_interval[0]} to {dt_interval[1]}')
    if pg_conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
        pg_conn.rollback()
    query = f'''INSERT INTO neutron_counts (station, time, uncorrected, corrected, pressure) VALUES %s
    ON CONFLICT (time, station) DO UPDATE SET corrected = EXCLUDED.corrected'''
    psycopg2.extras.execute_values(pg_cursor, query, data, template=f'(\'{station}\',%s,%s,%s,%s)')
    pg_conn.commit()

def _fetch_one(interval, station):
    assert len(station) <= 4
    with pg_conn.cursor() as cursor:
        cursor.execute(integrity_query(*interval, PERIOD, 'neutron_counts', 'corrected'))
        gaps = cursor.fetchall()
        for gap in gaps:
            _obtain_nmdb(gap, station, cursor)
            cursor.execute(f'''INSERT INTO neutron_counts (station, time, uncorrected, corrected, pressure)
            SELECT %s, time, -999, -999, -999 FROM generate_series(%s,%s,'1 hour'::interval) time''', [station, *interval])
            if pg_cursor.rowcount > 0:
                logging.warning(f'Neutron: abandoning gaps [{pg_cursor.rowcount}]')
        cursor.execute(f'''SELECT corrected FROM generate_series(%s,%s,'1 hour'::interval) time
        LEFT JOIN neutron_counts n ON time=n.time AND station=\'{station}\' AND corrected > 0''', interval+interval)
        return numpy.array(cursor.fetchall())

def fetch(interval, stations):
    with ThreadPoolExecutor(workers=8) as executor:
        return np.column_stack(list(executor.map(_fetch_one, [interval for s in stations], stations)))

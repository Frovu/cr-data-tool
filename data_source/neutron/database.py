from data_source.muon.db_proxy import pg_conn
from core.sql_queries import integrity_query
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
    global nmdb_conn
    if not nmdb_conn:
        logging.info('Connecting to NMDB')
        nmdb_conn = pymysql.connect(
            host=os.environ.get('NMDB_HOST'),
            port=int(os.environ.get('NMDB_PORT', 0)),
            user=os.environ.get('NMDB_USER'),
            password=os.environ.get('NMDB_PASS'),
            database='nmdb')

def _obtain_nmdb(interval, station, pg_cursor):
    _connect_nmdb()
    dt_interval = [datetime.utcfromtimestamp(t) for t in interval]
    with nmdb_conn.cursor() as cursor:
        cursor.execute(f'''SELECT start_date_time, uncorrected, corr_for_efficiency, pressure_mbar
            FROM {station}_1h WHERE start_date_time >= %s AND start_date_time <= %s''', dt_interval)
        data = cursor.fetchall()
    logging.info(f'Neutron: obtain nmdb:{station} [{len(data)}] {dt_interval[0]} to {dt_interval[1]}')
    query = f'''INSERT INTO neutron_counts (station, time, uncorrected, corrected, pressure) VALUES %s
    ON CONFLICT (time, station) DO UPDATE SET corrected = EXCLUDED.corrected'''
    psycopg2.extras.execute_values(pg_cursor, query, data, template=f'(\'{station}\',%s,%s,%s,%s)')

def _fetch_one(interval, station):
    assert len(station) <= 4
    with pg_conn.cursor() as cursor:
        if pg_conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
            pg_conn.rollback()
        cursor.execute(integrity_query(*interval, PERIOD, 'neutron_counts', 'corrected'))
        if gaps := cursor.fetchall():
            for gap in gaps:
                _obtain_nmdb(gap, station, cursor)
            count = cursor.rowcount
            cursor.execute(f'''INSERT INTO neutron_counts (station, time, uncorrected, corrected, pressure)
            SELECT %s, time, -999, -999, -999 FROM generate_series(to_timestamp(%s),to_timestamp(%s),'1 hour'::interval) time
            ON CONFLICT DO NOTHING ''', [station, *interval])
            count = cursor.rowcount - count
            if count > 0:
                logging.warning(f'Neutron: closed gaps [{count}]')
            pg_conn.commit()
        cursor.execute(f'''SELECT corrected FROM generate_series(to_timestamp(%s),to_timestamp(%s),'1 hour'::interval) ts
        LEFT JOIN neutron_counts n ON ts=n.time AND station=\'{station}\' AND corrected > 0''', interval)
        return numpy.array(cursor.fetchall(), dtype=numpy.float32)

def fetch(interval, stations):
    return numpy.column_stack([_fetch_one(interval, s) for s in stations])

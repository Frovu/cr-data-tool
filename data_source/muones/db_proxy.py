from core.sql_queries import integrity_query
import logging
import os

import psycopg2
import psycopg2.extras
pg_conn = psycopg2.connect(
    dbname = os.environ.get("MUON_DB_NAME") or "cr_cr",
    user = os.environ.get("MUON_DB_USER") or "crdt",
    password = os.environ.get("MUON_DB_PASS"),
    host = os.environ.get("MUON_DB_HOST")
)

PERIODS = dict([
    # (86400, '24h'),
    (3600, '60m'),
    (60, '01m')
])

def _table_name(period, meteo=False):
    return f'muon_{"meteo" if meteo else "counts"}_{PERIODS[period]}'

for period in PERIODS:
    with pg_conn.cursor() as cursor:
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {_table_name(period)} (
        time TIMESTAMP NOT NULL,
        channel SMALLINT,
        source REAL,
        corrected REAL,
        UNIQUE (time, channel))''')
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {_table_name(period, 'meteo')} (
        time TIMESTAMP NOT NULL,
        station SMALLINT,
        pressure REAL,
        T_m REAL,
        UNIQUE (time, station))''')
        pg_conn.commit()

def stations():
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT name, lat, lon, (SELECT array_agg(channel_name) AS channels FROM muon_channels WHERE station_name = name) FROM muon_stations')
        result = []
        for s in cursor.fetchall():
            result.append({'name': s[0], 'lat': float(s[1]), 'lon': float(s[2]), 'channels': s[3]})
        return result

def station(lat, lon):
    with pg_conn.cursor() as cursor:
        cursor.execute(f'SELECT name FROM muon_stations WHERE round(lat::numeric,2) = %s AND round(lon::numeric,2) = %s', [round(lat, 2), round(lon, 2)])
        result = cursor.fetchone()
        return result and result[0]

class Channel:
    def init(self, station, channel, period):
        if not PERIODS.get(period):
            return None
        with pg_conn.cursor() as cursor:
            cursor.execute(f'''SELECT
id, channel_name, station_name, (SELECT id FROM muon_stations WHERE name = %s)
FROM muon_channels WHERE station_name = %s AND channel_name = %s''', [station, station, channel])
            result = cursor.fetchone()
        if not result:
            return None
        self.id, self.name, self.station_name, self.station_id = result
        self.period = period
        return self

def channel(station, channel, period):
    return Channel().init(station, channel, period)

def analyze_integrity(channel, interval, column):
    if type(columns) is list:
    for col in columns:
        if analyze_integrity(station, t_from, t_to, period, channel, col):
            return True
    return False
    q = integrity_query(*interval, channel.period, _table_name(station, period),
        columns, where=f'channel = \'{channel}\'')
    with pg_conn.cursor() as cursor:
        cursor.execute(q)
        return cursor.fetchall()

def select(channel, interval, columns=['count_corr'], include_time=True, order='time', where=''):
    with pg_conn.cursor() as cursor:
        q = f'''SELECT {"EXTRACT(EPOCH FROM time)," if include_time else ""}{",".join(columns)}
FROM {_table_name(station, period)} c LEFT JOIN {_table_name(station, period, 'meteo')} m
    ON (m.time = c.time AND m.station = {channel.station_id} AND c.channel = {channel.id})
WHERE time >= to_timestamp(%s) AND time <= to_timestamp(%s)
{"AND "+where if where else ""} ORDER BY {order}'''
        cursor.execute(q, [t_from, t_to])
        return cursor.fetchall(), (['time']+columns) if include_time else columns

def upsert(station, period, channel, data, columns, epoch=False):
    if not len(data): return
    with pg_conn.cursor() as cursor:
        query = f'''INSERT INTO {_table_name(station, period)} (channel, {", ".join(columns)}) VALUES %s
        ON CONFLICT (time, channel) DO UPDATE SET ({", ".join(columns)}) = ({", ".join([f"EXCLUDED.{f}" for f in columns])})'''
        tl = f'(\'{channel}\',{"to_timestamp(%s)" if epoch else "%s"},{",".join(["%s" for f in columns[1:]])})'
        psycopg2.extras.execute_values (cursor, query, data, template=tl)
        pg_conn.commit()
        logging.info(f'Upsert: {_table_name(station, period)}/{channel} <-[{len(data)}] {",".join(columns[-2:])} from {data[0][0]}')

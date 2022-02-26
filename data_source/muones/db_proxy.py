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
    # (60, '01m'),
    (3600, '60m')
])

def _table(period):
    return f'muon_counts_{PERIODS[period]}'
def _table_cond(period):
    return f'muon_conditions_{PERIODS[period]}'

for _period in PERIODS:
    with pg_conn.cursor() as cursor:
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {_table(_period)} (
        time TIMESTAMP NOT NULL,
        channel SMALLINT,
        source REAL,
        corrected REAL,
        UNIQUE (time, channel))''')
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {_table_cond(_period)} (
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
            cursor.execute(f'''SELECT c.id, s.id, lat, lon
FROM muon_channels c JOIN muon_stations s ON s.name = c.station_name
WHERE station_name = %s AND channel_name = %s''', [station, channel])
            result = cursor.fetchone()
        if not result:
            return None
        self.id, self.station_id, lat, lon = result
        self.station_name, self.name = station, channel
        self.period, self.coordinates = period, (float(lat), float(lon))
        return self

def channel(station, channel, period):
    return Channel().init(station, channel, period)

def analyze_integrity(channel, interval, columns):
    td, tc = _table(channel.period), _table_cond(channel.period)
    j = f'''LEFT JOIN {td} ON (ser.tm = {td}.time AND channel = {channel.id})
        LEFT JOIN {tc} ON (ser.tm = {tc}.time AND station = {channel.station_id})'''
    with pg_conn.cursor() as cursor:
        cursor.execute(integrity_query(*interval, channel.period, [], columns, join_overwrite=j))
        return cursor.fetchall()

def select(channel, interval, columns=['count_corr'], include_time=True, order='time', where=''):
    with pg_conn.cursor() as cursor:
        q = f'''SELECT {"EXTRACT(EPOCH FROM c.time)," if include_time else ""}{",".join(columns)}
FROM {_table(channel.period)} c LEFT JOIN {_table_cond(channel.period)} m
    ON (m.time = c.time AND m.station = {channel.station_id} AND c.channel = {channel.id})
WHERE c.time >= to_timestamp(%s) AND c.time <= to_timestamp(%s)
{"AND "+where if where else ""} ORDER BY {order}'''
        cursor.execute(q, interval)
        return cursor.fetchall(), (['time']+columns) if include_time else columns

def upsert(channel, data, column, epoch=False):
    if not len(data): return
    is_counts = column in ['source', 'corrected']
    table = _table(channel.period) if is_counts else _table_cond(channel.period)
    fk_col, fk_val = ('channel', channel.id) if is_counts else ('station', channel.station_id)
    with pg_conn.cursor() as cursor:
        query = f'''INSERT INTO {table} (time, {fk_col}, {column}) VALUES %s
        ON CONFLICT (time, {fk_col}) DO UPDATE SET {column} = EXCLUDED.{column}'''
        template = f'({"to_timestamp(%s)" if epoch else "%s"},{fk_val},%s)'
        psycopg2.extras.execute_values (cursor, query, data, template=template)
        pg_conn.commit()
        logging.info(f'Upsert: {table}{("/"+channel.name) if is_counts else ""} <-[{len(data)}] {column} from {data[0][0]}')

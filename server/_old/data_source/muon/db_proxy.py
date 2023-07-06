from core.sql_queries import integrity_query, remove_spikes
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
C_COLUMNS = ['source', 'corrected', 'T_eff']

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
        T_eff REAL,
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
        cursor.execute(f'SELECT name, lat, lon, (SELECT array_agg(channel_name ORDER BY id) AS channels FROM muon_channels WHERE station_name = name) FROM muon_stations ORDER BY id')
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
            cursor.execute(f'''SELECT EXTRACT(EPOCH from since), c.id, s.id, lat, lon, dir_vertical, coef_pressure, coef_tm, mean_pressure, mean_tm, coef_per_len
FROM muon_channels c JOIN muon_stations s ON s.name = c.station_name
WHERE station_name = %s AND channel_name = %s''', [station, channel])
            result = cursor.fetchone()
        if not result:
            return None
        self.since, self.id, self.station_id, lat, lon, self.angle, self.coef_pr, self.coef_tm, self.mean_pr, self.mean_tm, self.coef_len = result
        self.station_name, self.name = station, channel
        self.period, self.coordinates = period, (float(lat), float(lon))
        return self

    def update_coefs(self, c_pr, c_tm, m_pr, m_tm, c_len):
        with pg_conn.cursor() as cursor:
            cursor.execute('''UPDATE muon_channels SET coef_pressure = %s, coef_tm = %s, mean_pressure = %s,
            mean_tm = %s, coef_per_len = %s WHERE id = %s''', [c_pr, c_tm, m_pr, m_tm, c_len, self.id])
            pg_conn.commit()

def channel(station, channel, period):
    return Channel().init(station, channel, period)

def analyze_integrity(channel, interval, columns):
    td, tc = _table(channel.period), _table_cond(channel.period)
    j = f'''LEFT JOIN {td} ON (ser.tm = {td}.time AND channel = {channel.id})
        LEFT JOIN {tc} ON (ser.tm = {tc}.time AND station = {channel.station_id})'''
    with pg_conn.cursor() as cursor:
        cursor.execute(integrity_query(*interval, channel.period, [], columns, join_overwrite=j))
        return cursor.fetchall()

def select(channel, interval, columns, include_time=True, order='c.time', where=''):
    with pg_conn.cursor() as cursor:
        q = f'''SELECT {"EXTRACT(EPOCH FROM c.time)," if include_time else ""}{",".join(columns)}
FROM {_table(channel.period)} c LEFT JOIN {_table_cond(channel.period)} m ON m.time = c.time
WHERE c.time >= to_timestamp(%s) AND c.time <= to_timestamp(%s)
AND m.station = {channel.station_id} AND c.channel = {channel.id}
{"AND "+where if where else ""} ORDER BY {order}'''
        try:
            cursor.execute(q, interval)
            return cursor.fetchall(), (['time']+columns) if include_time else columns
        except psycopg2.errors.InFailedSqlTransaction:
            pg_conn.rollback()
            logging.warning(f'Muon: InFailedSqlTransaction on select, rolling back')
            return select(channel, interval, columns, include_time, order, where)

def upsert(channel, data, column, epoch=False):
    if not len(data): return
    is_counts = column in C_COLUMNS
    table = _table(channel.period) if is_counts else _table_cond(channel.period)
    fk_col, fk_val = ('channel', channel.id) if is_counts else ('station', channel.station_id)
    try:
        with pg_conn.cursor() as cursor:
            query = f'''INSERT INTO {table} (time, {fk_col}, {column}) VALUES %s
            ON CONFLICT (time, {fk_col}) DO UPDATE SET {column} = EXCLUDED.{column}'''
            template = f'({"to_timestamp(%s)" if epoch else "%s"},{fk_val},%s)'
            psycopg2.extras.execute_values (cursor, query, data, template=template)
            pg_conn.commit()
    except psycopg2.errors.InFailedSqlTransaction:
        pg_conn.rollback()
        logging.warning(f'Muon: InFailedSqlTransaction on upsert, rolling back')
        return upsert(channel, data, column, epoch)
    logging.info(f'Upsert: muon:{channel.station_name}{("/"+channel.name) if is_counts else ""} <-[{len(data)}] {column} from {data[0][0]}')

def clear(channel, column):
    is_counts = column in C_COLUMNS
    table = _table(channel.period) if is_counts else _table_cond(channel.period)
    fk_col, fk_val = ('channel', channel.id) if is_counts else ('station', channel.station_id)
    with pg_conn.cursor() as cursor:
        query = f'UPDATE {table} SET {column} = NULL WHERE {fk_col} = {fk_val}'
        cursor.execute(query)
        pg_conn.commit()
    logging.info(f'Clear: muon:{channel.station_name}/{channel.name} {column}')
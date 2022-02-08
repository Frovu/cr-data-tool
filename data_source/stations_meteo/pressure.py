import data_source.stations_meteo.data as meteo
import data_source.stations_meteo.db_proxy as proxy
import data_source.muones.obtain_data as muones
from datetime import datetime, timedelta
import psycopg2.extras
import logging
pg_conn = proxy.pg_conn

def _parse_fcrl_one(year, mon, columns=['Pr']):
    data = []
    dir = '/mnt/cr55/FCRL_Data/Result/'
    if datetime.now().year != year or datetime.now().month != mon:
        dir += 'Result_Pre_Final/'
    with open(f'{SRC}{(year%100):02d}{month:02d}FCRL_Result.60u.txt') as f:
        lines = f.readlines()
    indexes = [lines[0].split().index(c) for c in columns]
    for line in lines[2:]:
        sp = line.split()
        time = sp[0]+' '+sp[1]
        data.append([DEVICE_ID, time] + [sp[i] for i in indexes])
    with pg_conn.cursor() as cursor:
        q = f'INSERT INTO pressure (time, fcrl) VALUES %s ON CONFLICT(time) DO UPDATE SET fcrl = EXCLUDED.fcrl'
        psycopg2.extras.execute_values(cursor, q, data)
        pg_conn.commit()

def _fetch_fcrl(t_from, t_to):
    dt = datetime.utcfromtimestamp(t_from)
    mon_from = datetime(dt.year, dt.month, 1)
    while mon_from.timestamp() < t_to:
        _parse_fcrl_one(mon_from.year, mon_from.month)
        mon_from += timedelta(days=1)

def _fetch_muon(t_from, t_to, station='Moscow', period=3600):
    logging.debug(f'P: fetching muon {t_from}:{t_to}')
    data = muones.obtain_raw(station, t_from, t_to, period, fields=['pressure'])[0]
    logging.debug(f'P: fetching muon - done [{len(data)}]')
    with pg_conn.cursor() as cursor:
        q = f'INSERT INTO pressure (time, muon_pioneer) VALUES %s ON CONFLICT(time) DO UPDATE SET muon_pioneer = EXCLUDED.muon_pioneer'
        psycopg2.extras.execute_values(cursor, q, data, template='(to_timestamp(%s),%s)')
        pg_conn.commit()

def _fetch_meteo(lat, lon, tf, tt):
    logging.debug(f'P: fetching meteo {tf}:{tt}')
    import time
    for i in range(1000):
        status, data = meteo.get_with_model(lat, lon, tf, tt)
        if status != 'ok':
            logging.debug(f'P/rmp: {status}:{data}')
        else:
            logging.debug(f'P/rmp: {status}')
            return True
        time.sleep(3)

def get(lat, lon, t_from, t_to, period=3600):
    if (lat, lon) != (55.47, 37.32):
        return None;
    with pg_conn.cursor() as cursor:
        query = f'''CREATE TABLE IF NOT EXISTS pressure (
        time TIMESTAMP NOT NULL PRIMARY KEY,
        fcrl REAL,
        muon_pioneer REAL)'''
        cursor.execute(query)
        pg_conn.commit()
    # _fetch_fcrl(t_from, t_to)
    _fetch_muon(t_from, t_to)
    _fetch_meteo(lat, lon, t_from, t_to)
    with pg_conn.cursor() as cursor:
        q = '''SELECT EXTRACT(EPOCH FROM p.time), l.pressure, p.fcrl, p.muon_pioneer
        FROM pressure p INNER JOIN local_moscow l ON (l.time = p.time)
        WHERE p.time >= to_timestamp(%s) AND p.time <= to_timestamp(%s) ORDER BY p.time'''
        cursor.execute(q, [t_from, t_to])
        return cursor.fetchall()

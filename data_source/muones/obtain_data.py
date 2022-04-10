import os
import psycopg2
import logging
from datetime import datetime, timedelta
from core.sql_queries import integrity_query
import requests
import json

def _psql_query(table, period, t_from, t_to, fields, epoch=False, count=False, cond=''):
    interval = f'interval \'{period} seconds\''
    return f'''WITH periods AS
(SELECT generate_series(to_timestamp({t_from}), to_timestamp({t_to}), {interval}) period)
SELECT {'EXTRACT(EPOCH FROM period)::integer' if epoch else 'period'} AS time,{'COUNT(*),'if count else ''}{', '.join([f'ROUND(AVG({f})::numeric, 3)::real as {f}' for f in fields[1:]])}
FROM periods LEFT JOIN {table} ON (period <= {fields[0]} AND {fields[0]} < period + {interval} {cond})
GROUP BY period ORDER BY period
'''

def _obtain_nagoya(dt_from, dt_to, what):
    year, month = dt_from.year, dt_from.month
    dir = f'tmp/Nagoya/{what}'
    result = []
    while year < dt_to.year or (year == dt_to.year and month <= dt_to.month):
        fpath = f'{dir}/{year%100:02}{month:02}.txt'
        if os.path.exists(fpath):
            with open(fpath) as file:
                for line in file:
                    date, time, value = line.split()
                    time = datetime.strptime(date+'T'+time, '%Y-%m-%dT%H:%M:%S+00') # meh
                    result.append((time, float(value)))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return result

def _obtain_gmdn(station, dt_from, dt_to, what):
    # FIXME: some station will not have Pres. column
    is_channel = what != 'pressure'
    col_name = what if is_channel else 'Pres.'
    dir = next(d for d in os.listdir('tmp/gmdn') if station in d)
    result = []
    for year in range(dt_from.year, dt_to.year + 1):
        fpath = f'tmp/gmdn/{dir}/{year}.txt'
        if not os.path.exists(fpath):
            continue
        with open(fpath) as file:
            for line in file:
                if '*'*32 in line:
                    columns = last.split()
                    break
                last = line
            idx = columns.index(col_name)
            for line in file:
                split = line.split()
                time = datetime(*[int(i) for i in split[:4]])
                val = (float(split[idx]) / 60) if is_channel else float(split[idx]) # /60 for ppm
                result.append([time, val])
    return result

def _obtain_apatity(station, t_from, t_to, channel='V', what='source', period=3600):
    url = 'https://cosmicray.pgia.ru/json/db_query_mysql.php'
    dbn = 'full_muons' if station == 'Apatity' else 'full_muons_barentz'
    res = requests.get(f'{url}?db={dbn}&start={t_from}&stop={t_to}&interval={period//60}')
    if res.status_code != 200:
        logging.warning(f'Muones: failed raw -{res.status_cod}- {station}:{channel} {t_from}:{t_to}')
        return []
    target = 'pressure_mu' if what == 'pressure' else 'mu_dn'
    data = json.loads(res.text)
    if not data:
        trim = datetime.now().timestamp() // period * period - period
        stop = int(trim) if t_to > trim else t_to
        return [(datetime.utcfromtimestamp(t), -1) for t in range(t_from, stop+1, period)]
    result = []
    for line in data:
        time = datetime.utcfromtimestamp(int(line['timestamp']) // period * period)
        result.append([time, line[target]])
    logging.debug(f'Muones: got raw [{len(result)}/{(t_to-t_from)//period+1}] {station}:{channel} {t_from}:{t_to}')
    return result

def obtain(channel, t_from, t_to, column):
    station = channel.station_name
    logging.debug(f'Muones: querying raw {station}:{channel.name} {t_from}:{t_to}')
    if station == 'Moscow-pioneer':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            with conn.cursor() as cursor:
                col = 'n_v' if column == 'source' else column
                cursor.execute(_psql_query('muon_data', channel.period, t_from, t_to, ['dt', col]))
                resp = cursor.fetchall()
                return resp, column
    elif station == 'Nagoya':
        what = column if column == 'pressure' else channel.name
        dt_from, dt_to = [datetime.utcfromtimestamp(t) for t in [t_from, t_to]]
        result = _obtain_gmdn(station, dt_from, dt_to, what)
        if not result:
            return _obtain_nagoya(dt_from, dt_to, what), column
        if result[0][0] > dt_from:
            result = _obtain_nagoya(dt_from, result[0][0]-timedelta(hours=1), what) + result
        if result[-1][0] < dt_to:
            result = result + _obtain_nagoya(result[-1][0]+timedelta(hours=1), dt_to, what)
        return result, column
    elif station in ['Apatity', 'Barentsburg']:
        data = _obtain_apatity(station, t_from, t_to, channel.name, column)
        return data, column

def obtain_raw(station, t_from, t_to, period, fields=None):
    if station == 'Moscow-pioneer':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            fl = ['dt', 'c0', 'c1', 'n_v', 'pressure', 'temperature', 'temperature_ext', 'voltage']
            with conn.cursor() as cursor:
                q = _psql_query('muon_data', period, t_from, t_to, [fl[0]] + fields if fields else fl, epoch=True, count=False)
                cursor.execute(q)
                return cursor.fetchall(), [desc[0] for desc in cursor.description]

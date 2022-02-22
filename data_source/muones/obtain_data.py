import os
import psycopg2
import logging
from datetime import datetime
from core.sql_queries import integrity_query

FIELDS = {
    'Moscow': ['dt', 'c0', 'c1', 'n_v', 'pressure', 'temperature', 'temperature_ext', 'voltage']
}

def _psql_query(table, period, t_from, t_to, fields, epoch=False, count=True, cond=''):
    interval = f'interval \'{period} seconds\''
    return f'''WITH periods AS
(SELECT generate_series(to_timestamp({t_from}), to_timestamp({t_to}), {interval}) period)
SELECT {'EXTRACT(EPOCH FROM period)::integer' if epoch else 'period'} AS time,{'COUNT(*),'if count else ''}{', '.join([f'ROUND(AVG({f})::numeric, 3)::real as {f}' for f in fields[1:]])}
FROM periods LEFT JOIN {table} ON (period <= {fields[0]} AND {fields[0]} < period + {interval} {cond})
GROUP BY period ORDER BY period
'''

def _obtain_gmdn(station, t_from, t_to, channel):
    # FIXME: some station will not have Pres. column
    dir = next(d for d in os.listdir('tmp/gmdn') if station in d)
    dt_from, dt_to = [datetime.utcfromtimestamp(t) for t in [t_from, t_to]]
    result = []
    for year in range(dt_from.year, dt_to.year + 1):
        with open(f'tmp/gmdn/{dir}/{year}.txt') as file:
            for line in file:
                if '*'*32 in line:
                    columns = last.split()
                    break
                last = line
            pres_idx = columns.index('Pres.')
            chan_idx = columns.index(channel)
            for line in file:
                split = line.split()
                time = datetime(*[int(i) for i in split[:4]])
                result.append([time, float(split[chan_idx]) / 60, float(split[pres_idx]])) # /60 for ppm
    return result

def obtain(station, period, t_from, t_to, channel):
    logging.debug(f'Muones: querying raw ({station})[{period}] {t_from}:{t_to}')
    if station == 'Moscow':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            with conn.cursor() as cursor:
                cursor.execute(_psql_query('muon_data', period, t_from, t_to, ['dt', 'n_v', 'pressure']))
                    # cond='AND device_id=(SELECT id FROM devices WHERE key = \'muon-pioneer\')'))
                resp = cursor.fetchall()
                return resp, ['time', 'raw_acc_cnt', 'count_raw', 'pressure']
    elif station in ['Nagoya']:
        data = _obtain_gmdn(station, t_from, t_to, channel)
        return data, ['time', 'count_corr_p', 'pressure']

def obtain_raw(station, t_from, t_to, period, fields=None):
    if station == 'Moscow':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            with conn.cursor() as cursor:
                q = _psql_query('muon_data', period, t_from, t_to, [FIELDS["Moscow"][0]] + fields if fields else FIELDS["Moscow"], epoch=True, count=False)
                    # cond='AND device_id=(SELECT id FROM devices WHERE key = \'muon-pioneer\')')
                cursor.execute(q)
                return cursor.fetchall(), [desc[0] for desc in cursor.description]

import os
import psycopg2
import logging
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

def obtain(station, period, t_from, t_to):
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
                return resp

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

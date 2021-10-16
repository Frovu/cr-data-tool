import os
import psycopg2
import logging
from core.sql_queries import integrity_query

FIELDS = {
    'Moscow': ['date_reg', 'c1', 'c2', 'n_v', 'pressure', 'temperature', 'temperature_ext', 'voltage']
}

def _psql_query(table, period, t_from, t_to, fields, epoch=False, count=True):
    interval = f'interval \'{period} seconds\''
    return f'''WITH periods AS
(SELECT generate_series(to_timestamp({t_from}), to_timestamp({t_to}), {interval}) period)
SELECT {'EXTRACT(EPOCH FROM period)::integer' if epoch else 'period'} AS time,{'COUNT(*),'if count else ''}{', '.join([f'ROUND(AVG({f})::numeric, 2)::real as {f}' for f in fields[1:]])}
FROM periods LEFT JOIN {table} ON (period <= {fields[0]} AND {fields[0]} < period + {interval} AND dev=0)
GROUP BY period ORDER BY period
'''
#on (period <= date_reg AND date_reg < period + interval '4 hours') group by period order by period;

def obtain(station, period, t_from, t_to):
    logging.debug(f'Muones: querying raw ({station})[{period}] {t_from}:{t_to}')
    if station == 'Moscow':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            with conn.cursor() as cursor:
                cursor.execute(_psql_query('data', period, t_from, t_to, ['date_reg', 'n_v', 'pressure']))
                resp = cursor.fetchall()
                return resp

def obtain_raw(station, t_from, t_to, period):
    if station == 'Moscow':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            with conn.cursor() as cursor:
                q = _psql_query('data', period, t_from, t_to, FIELDS["Moscow"], epoch=True, count=False)
                cursor.execute(q, [t_from, t_to])
                return cursor.fetchall(), [desc[0] for desc in cursor.description]

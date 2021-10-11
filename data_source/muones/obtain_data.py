import os
import psycopg2
import logging

def _psql_query(table, period, t_from, t_to, fields):
    interval = f'interval \'{period} seconds\''
    return f'''WITH periods AS
(SELECT generate_series(to_timestamp({t_from}), to_timestamp({t_to}), {interval}) period)
SELECT period AS time, COUNT(*), {', '.join([f'ROUND(AVG({f})::numeric, 2)' for f in fields[1:]])}
FROM periods LEFT JOIN {table} ON (period <= {fields[0]} AND {fields[0]} < period + {interval} AND dev=0)
GROUP BY period ORDER BY period
'''
#on (period <= date_reg AND date_reg < period + interval '4 hours') group by period order by period;

def obtain(station, period, t_from, t_to):
    if station == 'Moscow':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            with conn.cursor() as cursor:
                cursor.execute(_psql_query('data', period, t_from, t_to, ['date_reg', 'n_v', 'pressure']))
                resp = cursor.fetchall()
                return resp

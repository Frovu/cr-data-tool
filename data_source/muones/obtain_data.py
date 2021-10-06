import os
import psycopg2
from datetime import datetime, timezone

def _psql_query(table, dt_from, dt_to, period, fields):
    t_from = dt_from.replace(tzinfo=timezone.utc).timestamp()
    t_to = dt_to.replace(tzinfo=timezone.utc).timestamp()
    interval = f'interval \'{period} seconds\''
    return f'''WITH periods AS
(SELECT generate_series(to_timestamp({t_from}), to_timestamp({t_to}), {interval}) period)
SELECT COUNT(*), period AS time, {', '.join([f'ROUND(AVG({f})::numeric, 2)' for f in fields[1:]])}
FROM periods LEFT JOIN {table} ON (period <= {fields[0]} AND {fields[0]} < period + {interval})
GROUP BY period ORDER BY period
'''
#on (period <= date_reg AND date_reg < period + interval '4 hours') group by period order by period;

def obtain(station, dt_from, dt_to, period=3600):
    if station == 'Moscow':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            with conn.cursor() as cursor:
                cursor.execute(_psql_query('data', dt_from, dt_to, period, ['date_reg', 'n_v', 'pressure']))
                resp = cursor.fetchall()
                return resp
                # return _align_to_period(resp, period)

dt_strt = datetime(2021, 10, 5)
dt_end = datetime(2021, 10, 7)
for r in obtain('Moscow', dt_strt, dt_end):
    print(*r)

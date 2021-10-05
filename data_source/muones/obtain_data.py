import os
import psycopg2
from datetime import datetime, timezone

def psql_query(table, dt_from, dt_to, fields):
    return f'''SELECT {",".join(fields)} FROM {table}
WHERE {fields[0]} >= to_timestamp({dt_from.timestamp()})
  AND {fields[0]} <= to_timestamp({dt_to.timestamp()})'''

def obtain(station, dt_from, dt_to, period=3600):
    if station == 'Moscow':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            with conn.cursor() as cursor:
                cursor.execute(psql_query('data', dt_from, dt_to, ['date_reg', 'n_v', 'pressure']))
                resp = cursor.fetchall()
                for row in resp:
                    print(row)

dt_strt = datetime(2021, 8, 1, 12, 20)
print(dt_strt)
print(dt_strt.replace(tzinfo=timezone.utc))
dt_end = datetime(2021, 8, 1, 12, 30)
obtain('Moscow', dt_strt, dt_end)

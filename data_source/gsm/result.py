from data_source.muones.db_proxy import pg_conn
import numpy

with pg_conn.cursor() as cursor:
    cursor.execute('''CREATE TABLE IF NOT EXISTS gsm_result (
    time TIMESTAMP NOT NULL UNIQUE,
    A10 REAL, Ax REAL, Ay REAL, Az REAL, Axy REAL)''')
    pg_conn.commit()

def _select(interval, what):
    with pg_conn.cursor() as cursor:
        q = f'SELECT {what} FROM gsm_result WHERE time >= to_timestamp(%s) AND time <= to_timestamp(%s) ORDER BY time'
        cursor.execute(q, interval)
        return numpy.array(cursor.fetchall())

def get(interval, what=None):
    if not what:
        res = _select(interval, 'A10,Ax,Ay,Az')
        return [res[:,i] for i in range(4)]
    return _select(interval, what)

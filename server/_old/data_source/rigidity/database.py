from data_source.rigidity.cutoff import CutoffParams
from data_source.muon.proxy import pg_conn
from datetime import datetime, timedelta

TABLE_NAME = 'cutoff_rigidity'
MODELS = dict({
    'IGRF': 0
})

with pg_conn.cursor() as cursor:
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    time TIMESTAMP NOT NULL,
    params_hash BIGINT NOT NULL,
    model SMALLINT NOT NULL,
    effective REAL,
    lower REAL,
    upper REAL,
    UNIQUE(time, params_hash))''')
    pg_conn.commit()

def select(time, hash, model='', tolerance=timedelta(days=30)):
    if not tolerance:
        tolerance = timedelta(hours=6)
    assert not model or MODELS.get(model)
    with pg_conn.cursor() as cursor:
        query = f'SELECT effective FROM {TABLE_NAME} WHERE hash = %s AND time >= %s AND time <= %s' \
            + (' AND model = %s' if model else '')
        cursor.execute(query, [hash, time-tolerance, time+tolerance] + [MODELS[model]] if model else [])
        return cursor.fetchall()

def upsert(data):
    pass # TODO

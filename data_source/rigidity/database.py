from data_source.rigidity.cutoff import CutoffParams
from data_source.muones.proxy import pg_conn
from datetime import datetime, timedelta
import logging

TABLE_NAME = 'cutoff_rigidity'
MODELS = dict({
    'IGRF': 0
})

with pg_conn.cursor() as cursor:
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    time TIMESTAMP NOT NULL UNIQUE,
    model SMALLINT NOT NULL,
    effective REAL,
    lower REAL,
    upper REAL)''')
    pg_conn.commit()

def select(params: CutoffParams, tolerance: timedelta=timedelta(days=30), model: str=''):
    if not tolerance:
        tolerance = timedelta(hours=6)
    assert not model or MODELS.get(model)
    with pg_conn.cursor() as cursor:
        query = f'SELECT effective FROM {TABLE_NAME} WHERE hash AND time >= %s AND time <= %s' \
            + (' AND model = %s' if model else '')
        cursor.execute(query, [time - tolerance, time + tolerance] + [MODELS[model]] if model else [])
        return cursor.fetchall()

def upsert(data):
    pass

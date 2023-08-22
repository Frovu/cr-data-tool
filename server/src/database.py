
import os, logging
from psycopg_pool import ConnectionPool

log = logging.getLogger('crdt')
pool = ConnectionPool(kwargs = {
	'dbname': 'crdt',
	'user': 'crdt',
	'password': os.environ.get('DB_PASSWORD'),
	'host': os.environ.get('DB_HOST')
})

def upsert_many(conn, table, columns, data, conflict_constraint='time', do_nothing=False, write_nulls=False, write_values=True):
	with conn.cursor() as cur, conn.transaction():
		tmpname = table.split('.')[-1] + '_tmp'
		cur.execute(f'CREATE TEMP TABLE {tmpname} (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP')
		with cur.copy(f'COPY {tmpname}({",".join(columns)}) FROM STDIN') as copy:
			for row in data:
				copy.write_row(row)
		cur.execute(f'INSERT INTO {table}({",".join(columns)}) SELECT {",".join(columns)} FROM {tmpname} ' +
			('ON CONFLICT DO NOTHING' if do_nothing else
			f'ON CONFLICT ({conflict_constraint}) DO UPDATE SET ' +
				 ','.join([f'{c} = EXCLUDED.{c}' if write_nulls else f'{c} = COALESCE(EXCLUDED.{c}, {table}.{c})' if write_values
				 	else f'{c} = COALESCE({table}.{c}, EXCLUDED.{c})'
				 	for c in columns if c not in conflict_constraint])))

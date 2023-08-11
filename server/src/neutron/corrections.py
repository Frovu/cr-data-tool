from database import pool, upsert_many

def get_minutes(station, timestamp):
	# FIXME: check if supports 1 min
	with pool.connection() as conn:
		curs = conn.execute(f'SELECT corrected FROM nm.{station}_1min ' + \
			'WHERE to_timestamp(%s) <= time AND time < to_timestamp(%s) + \'1 hour\'::interval ORDER BY time', [timestamp, timestamp])
		return curs.fetchall()
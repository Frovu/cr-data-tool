from database import pool, upsert_many
from neutron.neutron import filter_for_integration, integrate
import numpy as np

def get_minutes(station, timestamp):
	# FIXME: check if supports 1 min
	assert station.provides_1min

	with pool.connection() as conn:
		curs = conn.execute(f'SELECT corrected FROM nm.{station.id}_1min ' + \
			'WHERE to_timestamp(%s) <= time AND time < to_timestamp(%s) + \'1 hour\'::interval ORDER BY time', [timestamp, timestamp])
		raw = np.array(curs.fetchall(), 'f8')[:,0]
	filtered = filter_for_integration(raw)
	integrated = integrate(raw)

	return {
		'station': station.id,
		'raw': np.where(~np.isfinite(raw), None, raw).tolist(),
		'filtered': np.where(~np.isfinite(filtered), None, filtered).tolist(),
		'integrated': integrated if np.isfinite(integrated) else None
	}
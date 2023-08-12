from database import pool, upsert_many
from neutron.neutron import filter_for_integration, integrate, select, obtain_many
import time
import numpy as np

def get_minutes(station, timestamp):
	# FIXME: check if supports 1 min
	assert station.provides_1min

	with pool.connection() as conn:
		curs = conn.execute(f'SELECT corrected FROM nm.{station.id}_1min ' + \
			'WHERE to_timestamp(%s) <= time AND time < to_timestamp(%s) + \'1 hour\'::interval ORDER BY time', [timestamp, timestamp])
		raw = np.array(curs.fetchall(), 'f8')[:,0]
	copy = np.copy(raw)
	filtered = filter_for_integration(copy)
	integrated = integrate(copy)

	return {
		'station': station.id,
		'raw': np.where(~np.isfinite(raw), None, raw).tolist(),
		'filtered': np.where(~np.isfinite(filtered), None, filtered).tolist(),
		'integrated': integrated if np.isfinite(integrated) else None
	}

def refetch(interval, stations):
	t0 = time.time()
	stids = [s.id for s in stations]
	old_data = np.array(select(interval, stids))
	obtain_many(interval, stations)
	new_data = np.array(select(interval, stids))

	assert old_data.shape == new_data.shape
	counts = { s: np.count_nonzero(old_data[:,i+1] != new_data[:,i+1]) for i, s in enumerate(stids) }

	return {
		'duration': time.time() - t0,
		'changeCounts': counts
	}
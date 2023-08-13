from database import pool, upsert_many
from neutron.neutron import filter_for_integration, integrate, select, fetch, obtain_many, update_result_table
from datetime import datetime
import time, logging
import numpy as np
log = logging.getLogger('crdt')

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
	log.info(f'Neutron: completed refetch {",".join(stids)} {interval[0]}:{interval[1]}')

	return {
		'duration': time.time() - t0,
		'changeCounts': counts
	}

def fetch_rich(interval, stations):
	rows_rev, fields = fetch(interval, stations)
	t_from, t_to = rows_rev[0][0], rows_rev[-1][0]
	with pool.connection() as conn:
		corrected = [np.array(conn.execute(f'SELECT corrected FROM generate_series(to_timestamp(%s), to_timestamp(%s), \'1 hour\'::interval) tm ' +\
			f'LEFT JOIN nm.{st}_1h ON time = tm', [t_from, t_to]).fetchall())[:,0] for st in stations]
	times = np.arange(t_from, t_to+1, 3600)

	return {
		'fields': fields,
		'corrected': np.column_stack([times, *corrected]).tolist(),
		'revised': rows_rev
	}

def revision(stationRevisions):
	with pool.connection() as conn:
		for sid in stationRevisions:
			revs = np.array(stationRevisions[sid], dtype='object')
			revs[:,0] = np.array([datetime.utcfromtimestamp(t) for t in revs[:,0]])
			# TODO: insert author, comment
			log.info(f'Neutron: inserting revision of length {len(revs)} for {sid.upper()}')
			conn.execute('INSERT INTO neutron.revision_log (station, rev_time, rev_value)' +\
				'VALUES (%s, %s, %s)', [sid, revs[:,0].tolist(), revs[:,1].tolist()])
			upsert_many(conn, f'nm.{sid}_1h', ['time', 'revised'], revs.tolist(), write_nulls=True)
			update_result_table(conn, sid, [revs[0,0], revs[-1,0]])


import os, time, logging
from threading import Thread, Lock
from datetime import datetime
import numpy as np

from database import pool, upsert_many
from temperature import ncep
from muon.obtain_raw import obtain as obtain_raw

log = logging.getLogger('crdt')

obtain_mutex = Lock()
obtain_status = { 'status': 'idle' }

def _init():
	with open(os.path.join(os.path.dirname(__file__), './_init_db.sql'), encoding='utf-8') as file:
		init_text = file.read()
	with pool.connection() as conn:
		conn.execute(init_text)

_init()

def select(t_from, t_to, experiment, channel_name, query):
	fields = [f for f in query if f in ['original', 'revised', 'corrected', 't_mass_average', 'pressure' ]]
	query = ', '.join((f if f != 'revised' else 'COALESCE(revised, original) as revised' for f in fields)) 
	join_conditions = any((a in fields for a in ['t_mass_average', 'pressure']))
	with pool.connection() as conn:
		curs = conn.execute('SELECT EXTRACT(EPOCH FROM c.time)::integer as time, ' + query + \
			' FROM muon.counts_data c ' +\
			('LEFT JOIN muon.conditions_data m ON m.experiment = '+\
				' (SELECT id FROM muon.experiments WHERE name = %s) AND m.time = c.time ' if join_conditions else '') + \
			'WHERE channel = (SELECT id FROM muon.channels WHERE experiment = %s AND name = %s)' + \
			'AND to_timestamp(%s) <= c.time AND c.time <= to_timestamp(%s) ORDER BY c.time' \
			, [*[experiment]*(2 if join_conditions else 1), channel_name, t_from, t_to])
		return curs.fetchall(), [desc[0] for desc in curs.description]

def _do_obtain_all(t_from, t_to, experiment):
	global obtain_status
	try:
		with pool.connection() as conn:
			obtain_status = { 'status': 'busy' }
			row = conn.execute('SELECT id, lat, lon, operational_since, operational_until ' + \
				'FROM muon.experiments e WHERE name = %s', [experiment]).fetchone()
			if row is None:
				raise ValueError(f'Experiment not found: {experiment}')
			exp_id, lat, lon, since, until = row
			t_from = max(since.timestamp(), t_from)
			t_to   = min(until.timestamp(), t_to) if until is not None else t_to

			obtain_status['message'] = 'obtaining temperature..'
			while True:
				progress, result = ncep.obtain([t_from, t_to], lat, lon)
				obtain_status['downloading'] = progress
				if progress is None:
					break
				time.sleep(.1)
			if result is None:
				raise ValueError('NCEP returned None')
			t_m = result[:,1]
			times = np.array([datetime.utcfromtimestamp(t) for t in result[:,0]])
			data = np.column_stack((times, np.where(np.isnan(t_m), None, t_m))).tolist()
			upsert_many(conn, 'muon.conditions_data', ['experiment', 'time', 't_mass_average'],
				data, constants=[exp_id], conflict_constraint='time,experiment')
			
			obtain_status['message'] = 'obtaining pressure..'
			data = obtain_raw(t_from, t_to, experiment, 'pressure')
			upsert_many(conn, 'muon.conditions_data', ['experiment', 'time', 'pressure'],
				data, constants=[exp_id], conflict_constraint='time, experiment')
			
			obtain_status['message'] = 'obtaining counts..'
			channels = conn.execute('SELECT id, name FROM muon.channels WHERE experiment = %s', [experiment]).fetchall()
			for ch_id, ch_name in channels:
				obtain_status['message'] = 'obtaining counts: ' + ch_name
				data = obtain_raw(t_from, t_to, experiment, ch_name)
				upsert_many(conn, 'muon.counts_data', ['channel', 'time', 'original'],
					data, constants=[ch_id], conflict_constraint='time, channel')

			obtain_status = { 'status': 'ok' }
			
			# progr, data = ncep.obtain([t_from, t_to], lat, lon)
	except Exception as err:
		log.error('Failed muones obtain_all: %s', str(err))
		obtain_status = { 'status': 'error', 'message': str(err) }

def obtain_all(t_from, t_to, experiment):
	global obtain_status
	with obtain_mutex:
		if obtain_status['status'] != 'idle':
			saved = obtain_status
			if obtain_status['status'] in ['ok', 'error']:
				obtain_status = { 'status': 'idle' }
			return saved
		
		obtain_status = { 'status': 'busy' }
		Thread(target=_do_obtain_all, args=(t_from, t_to, experiment)).start()
		time.sleep(.1) # meh
		return obtain_status

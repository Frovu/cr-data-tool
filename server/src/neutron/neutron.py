from database import pool, upsert_many
from math import floor, ceil
from threading import Lock
from datetime import datetime
import os, logging
import numpy as np

from neutron.archive import obtain as obtain_from_archive
from neutron.nmdb import obtain as obtain_from_nmdb

log = logging.getLogger('crdt')

HOUR = 3600
obtain_mutex = Lock()
integrity_full = [None, None]
integrity_partial = [None, None]

def _init():
	with open(os.path.join(os.path.dirname(__file__), './_init_db.sql')) as file:
		init_text = file.read()
	with pool.connection() as conn:
		conn.execute(init_text)
		stations = conn.execute('SELECT id, provides_1min FROM neutron.stations').fetchall()
		for station, with_1min in stations:
			conn.execute(f'ALTER TABLE neutron.result ADD COLUMN IF NOT EXISTS {station} REAL')
			conn.execute(f'CREATE TABLE IF NOT EXISTS nm.{station}_1h (time TIMESTAMPTZ PRIMARY KEY, corrected REAL, revised REAL)')
			if not with_1min: continue
			conn.execute(f'CREATE TABLE IF NOT EXISTS nm.{station}_1min (time TIMESTAMPTZ PRIMARY KEY, corrected REAL)')
		ff, ft, pf, pt = conn.execute('SELECT full_from, full_to, partial_from, partial_to FROM neutron.integrity_state').fetchone()
		global integrity_full, integrity_partial
		integrity_full, integrity_partial = [ff, ft], [pf, pt]
_init()

def _save_integrity_state(conn):
	conn.execute('UPDATE neutron.integrity_state SET full_from=%s, full_to=%s, partial_from=%s, partial_to=%s', [*integrity_full, *integrity_partial])

def filter_for_integration(data):
	return data

def integrate(data):
	print(data)
	data = filter_for_integration(data)
	return np.sum(data, axis=0) / len(data)

def _obtain_similar(interval, stations, source, src_res=60):
	src_data = np.array({ 'nmdb': obtain_from_nmdb, 'archive': obtain_from_archive }[source](interval, stations))
	# TODO: use float dtype in array
	if not len(src_data):
		log.warn(f'Empty obtain ({source})!')
		return # TODO: handle smh

	res_dt_interval = [src_data[0][0], src_data[-1][0]]
	log.debug(f'Neutron: got [{len(src_data)} * {len(stations)}] /{src_res}')

	if src_res < HOUR:
		r_start, r_end = [d.timestamp() for d in res_dt_interval]
		first_full_h, last_full_h = ceil(r_start / HOUR) * HOUR, floor(r_end / HOUR) * HOUR
		length = (last_full_h - first_full_h) // HOUR + 1
		data = np.full((length, src_data.shape[1]), np.nan, src_data.dtype)
		data[:,0] = [datetime.utcfromtimestamp(t) for t in range(first_full_h, last_full_h+1, HOUR)]
		step = floor(HOUR / src_res)
		offset = floor((first_full_h - r_start) / src_res)
		integrated = (integrate(src_data[offset+i*step:offset+(i+1)*step, 1:]) for i in range(length))
		res = np.fromiter(integrated, np.dtype((float, data.shape[1]-1)))
		data[:,1:] = res
	else:
		data = src_data

	log.debug(f'Neutron: obtained {source} [{len(data)} * {len(stations)}] {res_dt_interval[0]} to {res_dt_interval[1]}')
	with pool.connection() as conn:
		for i, station in enumerate(stations):
			upsert_many(conn, f'nm.{station}_1h', ['time', 'corrected'],
				np.column_stack((data[:,0], data[:,1+i])))
			if src_res == 60:
				upsert_many(conn, f'nm.{station}_1min', ['time', 'corrected'],
					np.column_stack((src_data[:,0], src_data[:,1+i])))
			else:
				assert src_res == HOUR
		# TODO: insert corrected into result cach table
		# upsert_many(conn, 'neutron.result', ['time', *stations], data)
		conn.execute('INSERT INTO neutron.obtain_log(stations, source, interval_start, interval_end) ' +\
			'VALUES (%s, %s, %s, %s)', [stations, source, *res_dt_interval])

def _obtain_group(interval, group_partial=False):

	stations = ['APTY', 'CALG'] # TODO: determine stations by group

	# source = 'nmdb' if interval[1] >= datetime(datetime.now().year, 1, 1).timestamp() else 'local'
	_obtain_similar(interval, stations, 'nmdb')

def fetch(interval: [int, int], stations: list[str]):
	interval = (
		floor(interval[0] / HOUR) * HOUR,
		 ceil(min(interval[1], datetime.now().timestamp() - 2*HOUR) / HOUR) * HOUR
	)

	group_partial = True # TODO: actually distinguish full and partial integrity

	ips, ipe = integrity_partial if group_partial else integrity_full
	satisfied = ips and ipe and ips <= interval[0] and interval[1] <= ipe 

	with obtain_mutex:
		if not satisfied:
			req = (
				ipe if ipe and interval[0] >= ips else interval[0],
				ips if ips and interval[1] <= ipe else interval[1]
			)
			_obtain_group(req, group_partial)
	
	with pool.connection() as conn:
		curs = conn.execute(f'SELECT EXTRACT(EPOCH FROM ts)::integer as time, {",".join(stations)}' + \
			'FROM neutron.result WHERE %s <= time AND time <= %s', [*interval])
		return curs.fetchall(), [desc[0] for desc in curs.description]
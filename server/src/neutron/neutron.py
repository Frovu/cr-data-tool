from database import pool, upsert_many
from math import floor, ceil
from threading import Lock
from datetime import datetime, timezone
from dataclasses import dataclass
import os, logging
import numpy as np

from neutron.archive import obtain as obtain_from_archive
from neutron.nmdb import obtain as obtain_from_nmdb

log = logging.getLogger('crdt')

NMDB_SINCE = datetime(2020, 1, 1).replace(tzinfo=timezone.utc).timestamp()
HOUR = 3600
obtain_mutex = Lock()
integrity_full = [None, None]
integrity_partial = [None, None]
all_stations = []

@dataclass
class Station:
	id: str
	provides_1min: bool
	prefer_nmdb: bool

def _init():
	global integrity_full, integrity_partial, all_stations
	with open(os.path.join(os.path.dirname(__file__), './_init_db.sql')) as file:
		init_text = file.read()
	with pool.connection() as conn:
		conn.execute(init_text)
		rows = conn.execute('SELECT id, provides_1min, prefer_nmdb FROM neutron.stations').fetchall()
		all_stations = [Station(*r) for r in rows]
		for s in all_stations:
			conn.execute(f'ALTER TABLE neutron.result ADD COLUMN IF NOT EXISTS {s.id} REAL')
			conn.execute(f'CREATE TABLE IF NOT EXISTS nm.{s.id}_1h (time TIMESTAMPTZ PRIMARY KEY, corrected REAL, revised REAL)')
			if not s.provides_1min: continue
			conn.execute(f'CREATE TABLE IF NOT EXISTS nm.{s.id}_1min (time TIMESTAMPTZ PRIMARY KEY, corrected REAL)')
		ff, ft, pf, pt = conn.execute('SELECT full_from, full_to, partial_from, partial_to FROM neutron.integrity_state').fetchone()
		integrity_full, integrity_partial = [ff, ft], [pf, pt]
_init()

def _save_integrity_state(conn):
	conn.execute('UPDATE neutron.integrity_state SET full_from=%s, full_to=%s, partial_from=%s, partial_to=%s', [*integrity_full, *integrity_partial])

# filter everything <= 0
# filter spikes > 5 sigma
# filter station periods with < 50% coverage
def filter_for_integration(data):
	print(data)
	data[data <= 0] = np.nan
	std = np.nanstd(data, axis=0)
	med = np.nanmean(data, axis=0)
	print(np.where(np.abs(med - data) / std > 5))
	print()
	print(med, std)
	print()
	data[np.where(np.abs(med - data) / std > 5)] = np.nan
	data[:,np.where(np.count_nonzero(np.isfinite(data), axis=0) < len(data) / 2)] = np.nan
	return data

def integrate(data):
	data = filter_for_integration(data)
	return np.round(np.sum(data, axis=0) / len(data), 3)

def _obtain_similar(interval, stations, source):
	obtain_fn, src_res = { 'nmdb': (obtain_from_nmdb, 60), 'archive': (obtain_from_archive, 3600) }[source]
	src_data = obtain_fn(interval, stations)
	if not src_data:
		log.warn(f'Empty obtain ({source})!')
		return # TODO: handle smh
	
	src_data = np.array(src_data)

	res_dt_interval = [src_data[0][0], src_data[-1][0]]
	log.debug(f'Neutron: got [{len(src_data)} * {len(stations)}] /{src_res}')

	if src_res < HOUR:
		r_start, r_end = [d.replace(tzinfo=timezone.utc).timestamp() for d in res_dt_interval]
		first_full_h, last_full_h = ceil(r_start / HOUR) * HOUR, floor((r_end + src_res) / HOUR) * HOUR - HOUR
		length = (last_full_h - first_full_h) // HOUR + 1
		data = np.full((length, len(stations)+1), np.nan, src_data.dtype)
		data[:,0] = [datetime.utcfromtimestamp(t) for t in range(first_full_h, last_full_h+1, HOUR)]
		step = floor(HOUR / src_res)
		offset = floor((first_full_h - r_start) / src_res)
		fdata = np.vstack(src_data[:,1:].astype(float))
		integrated = (integrate(fdata[offset+i*step:offset+(i+1)*step]) for i in range(length))
		res = np.fromiter(integrated, np.dtype((float, len(stations))))
		# for i in range(len(stations))
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
		# TODO: insert revisions into result cache table
		upsert_many(conn, 'neutron.result', ['time', *stations], data)
		conn.execute('INSERT INTO neutron.obtain_log(stations, source, interval_start, interval_end) ' +\
			'VALUES (%s, %s, %s, %s)', [stations, source, *res_dt_interval])

def _obtain_group(interval, group_partial=False):
	# TODO: another criteria
	stations = [s for s in all_stations if not group_partial or s.prefer_nmdb]
	
	assert group_partial

	if interval[0] < NMDB_SINCE and NMDB_SINCE <= interval[1]:
		_obtain_group((interval[0], NMDB_SINCE-HOUR), group_partial)
		_obtain_group((NMDB_SINCE, interval[1]), group_partial)
		return log.debug('Neutron: split interval with NMDB_SINCE')

	nmdb_stations = [s.id for s in stations if s.prefer_nmdb] if interval[0] >= NMDB_SINCE else []
	nmdb_stations = ['KERG']
	if nmdb_stations:
		_obtain_similar(interval, nmdb_stations, 'nmdb')
	
	other_stations = [s.id for s in stations if s.id not in nmdb_stations]
	if not other_stations: return
	for s in other_stations:
		_obtain_similar(interval, [s], 'archive')

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
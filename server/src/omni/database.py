import os, json, logging, requests, re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from database import pool, upsert_many
from omni.derived import compute_derived

log = logging.getLogger('crdt')
omniweb_url = 'https://omniweb.gsfc.nasa.gov/cgi/nx1.cgi'
PERIOD = 3600

omni_columns = None
all_column_names = None
dump_info = None
dump_info_path = os.path.join(os.path.dirname(__file__), '../../data/omni_dump_info.json')

class OmniColumn:
	def __init__(self, name: str, owid: int, stub: str, is_int: bool=False):
		self.name = name
		self.omniweb_id = owid
		self.stub_value = stub
		self.is_int = is_int

def _init():
	global omni_columns, all_column_names, dump_info
	json_path = os.path.join(os.path.dirname(__file__), './database.json')
	vard_path = os.path.join(os.path.dirname(__file__), './omni_variables.txt')
	with open(json_path) as file, pool.connection() as conn:
		columns = json.load(file)
		cols = [f'{c} {columns[c][0]}' for c in columns]
		conn.execute(f'CREATE TABLE IF NOT EXISTS omni (\n{",".join(cols)})')
		for col in cols:
			conn.execute(f'ALTER TABLE omni ADD COLUMN IF NOT EXISTS {col}')
	omni_columns = []
	with open(vard_path) as file:
		for line in file:
			if not line.strip(): continue
			spl = line.strip().split()
			for column, [typedef, owid] in columns.items():
				if owid is None or spl[0] != str(owid):
					continue
				# Note: omniweb variables descriptions ids start with 1 but internally they start with 0, hence -1
				omni_columns.append(OmniColumn(column, owid - 1, spl[2], 'int' in typedef.lower()))
	all_column_names = [c.name for c in omni_columns] + [col for col, [td, owid] in columns.items() if owid is None and col != 'time']
	try:
		with open(dump_info_path) as file:
			dump_info = json.load(file)
	except:
		log.warn('Omniweb: Failed to read ' + str(dump_info_path))
_init()

def _obtain_omniweb(columns, interval):
	dstart, dend = [d.strftime('%Y%m%d') for d in interval]
	log.debug(f'Omniweb: querying {dstart}-{dend}')
	r = requests.post(omniweb_url, stream=True, data = {
		'activity': 'retrieve',
		'res': 'hour',
		'spacecraft': 'omni2',
		'start_date': dstart,
		'end_date': dend,
		'vars': [c.omniweb_id for c in columns]
	})
	if r.status_code != 200:
		log.warn('Omniweb: query failed - HTTP {r.status_code}')

	data = None
	for line in r.iter_lines(decode_unicode=True):
		if data is not None:
			if not line or '</pre>' in line:
				break
			try:
				split = line.split()
				time = datetime(int(split[0]), 1, 1, tzinfo=timezone.utc) + timedelta(days=int(split[1])-1, hours=int(split[2]))
				row = [time] + [(int(v) if c.is_int else float(v)) if v != c.stub_value else None for v, c in zip(split[3:], columns)]
				data.append(row)
			except:
				log.error('Omniweb: failed to parse line:\n' + line)
		elif 'YEAR DOY HR' in line:
			data = [] # start reading data
		elif 'INVALID' in line:
			correct_range = re.findall(r' (\d+)', line)
			new_range = [datetime.strptime(s, '%Y%m%d').replace(tzinfo=timezone.utc) for s in correct_range]
			if interval[1] < new_range[0] or new_range[1] < interval[0]:
				log.info(f'Omniweb: out of bounds')
				return 
			log.info(f'Omniweb: correcting range to fit {correct_range[0]}:{correct_range[1]}')
			return _obtain_omniweb(max(new_range[0], interval[0]), min(new_range[1], interval[1]))
	return data

def _obtain_izmiran(columns, interval):
	pass

def _cols(group, source='omniweb'):
	if group not in ['all', 'sw', 'imf']:
		raise ValueError('Bad param group')
	if source not in ['omniweb', 'ace', 'dscovr']:
		raise ValueError('Unknown source')
	sw_cols = [c for c in omni_columns if c.name in ['sw_speed', 'sw_density', 'sw_temperature']]
	imf_cols = [c for c in omni_columns if c.name in ['imf_scalar', 'imf_x', 'imf_y', 'imf_z']]
	return {
		'all': omni_columns if source == 'omniweb' else sw_cols + imf_cols,
		'sw': sw_cols,
		'imf': imf_cols
	}[group]

def obtain(source: str, interval: [int, int], group: str='all', overwrite=False):
	dt_interval = [datetime.utcfromtimestamp(t) for t in interval]

	query = _cols(group, source)
	res = {
		'omniweb': _obtain_omniweb,
		'ace': lambda g, i: _obtain_izmiran('ace', g, i),
		'dscovr': lambda g, i: _obtain_izmiran('dscovr', g, i),
	}[source](query, dt_interval)

	data, fields = compute_derived(res, [c.name for c in query])

	log.info(f'Omni: upserting *{group} from {source}: [{len(data)}] rows from {dt_interval[0]} to {dt_interval[1]}')
	with pool.connection() as conn:
		upsert_many(conn, 'omni', ['time', *fields], data, write_nulls=overwrite, write_values=overwrite)
	return len(data)

def remove(interval: [int, int], group):
	cols = [c.name for c in _cols(group)]
	with pool.connection() as conn:
		curs = conn.execute('UPDATE omni SET ' + ', '.join([f'{c} = NULL' for c in cols]) +
			' WHERE to_timestamp(%s) <= time AND time <= to_timestamp(%s)', interval)
		return curs.rowcount

def select(interval: [int, int], query=None, epoch=True):
	columns = [c for c in query if c in all_column_names] if query else all_column_names
	with pool.connection() as conn:
		curs = conn.execute(f'SELECT {"EXTRACT(EPOCH FROM time)::integer as" if epoch else ""} time, {",".join(columns)} ' +
			'FROM omni WHERE to_timestamp(%s) <= time AND time <= to_timestamp(%s) ORDER BY time', interval)
		return curs.fetchall(), [desc[0] for desc in curs.description]

def ensure_prepared(interval: [int, int]):
	global dump_info
	if dump_info and dump_info.get('from') <= interval[0] and dump_info.get('to') >= interval[1]:
		return
	log.info(f'Omni: beginning bulk fetch {interval[0]}:{interval[1]}')
	batch_size = 3600 * 24 * 1000
	with ThreadPoolExecutor(max_workers=4) as executor:
		for start in range(interval[0], interval[1]+1, batch_size):
			end = start + batch_size
			interv = [start, end if end < interval[1] else interval[1]]
			executor.submit(obtain, 'omniweb', interv)
	log.info(f'Omni: bulk fetch finished')
	with open(dump_info_path, 'w') as file:
		dump_info = { 'from': int(interval[0]), 'to': int(interval[1]), 'at': int(datetime.now().timestamp()) }
		json.dump(dump_info, file)
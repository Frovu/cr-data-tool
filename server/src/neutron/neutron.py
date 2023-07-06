from database import pool, upsert_many

from neutron.archive import obtain as obtain_from_archive
from neutron.nmdb import obtain as obtain_from_nmdb

def _init():
	with open(os.path.join(os.path.dirname(__file__), './_init_db.sql')) as file:
		init_text =  file.read()
	with pool.connection() as conn:
		conn.execute(init_text)
		stations = [r[0] for r in conn.execute('SELECT id, provides_1min FROM neutron.stations').fetchall()]
		for station, with_1min in stations:
			conn.execute(f'ALTER TABLE neutron.result ADD COLUMN IF NOT EXISTS {station} REAL')
			conn.execute(f'CREATE TABLE IF NOT EXISTS nm.{station}_1h (time TIMSTAMPTZ PRIMARY KEY, corrected REAL, revised REAL)')
			if not with_1min: continue
			conn.execute(f'CREATE TABLE IF NOT EXISTS nm.{station}_1min (time TIMSTAMPTZ PRIMARY KEY, corrected REAL)')
_init()


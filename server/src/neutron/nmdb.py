
import os, logging, pymysql.cursors, numpy
from threading import Timer, Lock, Thread
log = logging.getLogger('aides')

NMDB_KEEP_CONN_S = 180
nmdb_conn = None
discon_timer = None

def _disconnect_nmdb():
	global nmdb_conn, discon_timer
	if nmdb_conn:
		nmdb_conn.close()
		nmdb_conn = None
		log.debug('Disconnecting NMDB')
	discon_timer = None

def _connect_nmdb():
	global nmdb_conn, discon_timer
	if not nmdb_conn:
		log.info('Connecting to NMDB')
		nmdb_conn = pymysql.connect(
			host=os.environ.get('NMDB_HOST'),
			port=int(os.environ.get('NMDB_PORT', 3306)),
			user=os.environ.get('NMDB_USER'),
			password=os.environ.get('NMDB_PASS'),
			database='nmdb')
	if discon_timer:
		discon_timer.cancel()
		discon_timer = None
	discon_timer = Timer(NMDB_KEEP_CONN_S, _disconnect_nmdb)
	discon_timer.start()

# NOTE: This presumes that all data is 1-minute resolution and aligned
def obtain(interval, stations):
	_connect_nmdb()
	log.debug(f'Neutron: querying nmdb')
	dt_interval = [datetime.utcfromtimestamp(t) for t in interval]
	query = f'''
WITH RECURSIVE ser(time) AS (
	SELECT TIMESTAMP(%(from)s) UNION ALL 
	SELECT DATE_ADD(time, INTERVAL 1 minute) FROM ser WHERE time < %(to)s)
SELECT ser.time, {", ".join([st + '.val' for st in stations])} FROM ser\n'''
	for station in stations:
		query += f'''LEFT OUTER JOIN
(SELECT start_date_time as time, corr_for_efficiency as val
	FROM {station}_revori WHERE start_date_time >= %(from)s AND start_date_time < %(to)s + interval 1 hour
) {station} ON {station}.time = ser.time\n'''
	with nmdb_conn.cursor() as curs:
		try:
			curs.execute(query, {'from': dt_interval[0], 'to': dt_interval[1]})
		except:
			log.warning('Failed to query nmdb, disconnecting')
			return _disconnect_nmdb()
		data = curs.fetchall()
	return data

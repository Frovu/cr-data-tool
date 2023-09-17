
import os
from database import pool

def _init():
	with open(os.path.join(os.path.dirname(__file__), './_init_db.sql'), encoding='utf-8') as file:
		init_text = file.read()
	with pool.connection() as conn:
		conn.execute(init_text)

_init()

def select(t_from, t_to, station_name, channel_name, query):
	fields = [f for f in query if f in ['original', 'corrected', 'revised', 't_mass_average', 'pressure' ]]
	query = ', '.join(fields.replace('revised', 'COALESCE(revised, corrected) as revised')) 
	with pool.connection() as conn:
		return conn.execute('SELECT EXTRACT(EPOCH FROM c.time) as time, ' + query + \
			'FROM muon.counts_data c' +\
			('OUTER JOIN muon.conditions m ON m.station = ((SELECT id FROM muon.stations WHERE name = %s) m.time = c.time' \
				if any((a in fields for a in ['t_mass_average', 'pressure'])) else '') + \
			'WHERE channel = (SELECT id FROM muon.channels WHERE station_name = %s, channel_name = %s)' + \
			'AND to_timestamp(%s) <= time AND time <= to_timestamp(%s)', [station_name, channel_name, t_from, t_to]).fetchall()
	
def obtain_temperature(t_from, t_to, station_name):
	pass

def obtain_pressure(t_from, t_to, station_name):
	pass

def obtain_counts(t_from, t_to, station_name, channel_name, target='original'):
	pass
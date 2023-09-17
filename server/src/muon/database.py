
import os
from database import pool

def _init():
	with open(os.path.join(os.path.dirname(__file__), './_init_db.sql'), encoding='utf-8') as file:
		init_text = file.read()
	with pool.connection() as conn:
		conn.execute(init_text)

_init()

def select(t_from, t_to, experiment, channel_name, query):
	fields = [f for f in query if f in ['original', 'corrected', 'revised', 't_mass_average', 'pressure' ]]
	query = ', '.join((f if f != 'revised' else 'COALESCE(revised, corrected) as revised' for f in fields)) 
	join_conditions = any((a in fields for a in ['t_mass_average', 'pressure']))
	with pool.connection() as conn:
		curs = conn.execute('SELECT EXTRACT(EPOCH FROM c.time) as time, ' + query + \
			' FROM muon.counts_data c ' +\
			('LEFT JOIN muon.conditions_data m ON m.experiment = '+\
				' (SELECT id FROM muon.experiments WHERE name = %s) AND m.time = c.time ' if join_conditions else '') + \
			'WHERE channel = (SELECT id FROM muon.channels WHERE experiment = %s AND name = %s)' + \
			'AND to_timestamp(%s) <= c.time AND c.time <= to_timestamp(%s)' \
			, [*[experiment]*(2 if join_conditions else 1), channel_name, t_from, t_to])
		return curs.fetchall(), [desc[0] for desc in curs.description]
	
def obtain_temperature(t_from, t_to, experiment):
	pass

def obtain_pressure(t_from, t_to, experiment):
	pass

def obtain_counts(t_from, t_to, experiment, channel_name, target='original'):
	pass
import logging, json
from datetime import datetime
from database import pool
import statsmodels.api as sm
import numpy as np

HOUR = 3600
DAY = 24 * HOUR
log = logging.getLogger('crdt')

def _select(t_from, t_to, experiment, channel_name):
	fields = ['time', 'original', 'revised', 'pressure', 't_mass_average', 'a0', 'ax', 'ay', 'az']
	with pool.connection() as conn:
		exp_id, ch_id, lat, lon, corr_info = conn.execute(
			'''SELECT e.id, c.id, lat, lon, correction_info FROM muon.experiments e
			JOIN muon.channels c ON e.name = c.experiment
			WHERE e.name = %s AND c.name = %s''', [experiment, channel_name]).fetchone()
		res = conn.execute('''SELECT EXTRACT(EPOCH FROM c.time)::integer, original,
			NULLIF(COALESCE(revised, original), \'NaN\'), pressure, t_mass_average, a10, ax, ay, az
			FROM muon.counts_data c JOIN muon.conditions_data m
			ON m.experiment = %s AND c.channel = %s AND c.time = m.time
			JOIN gsm_result g ON g.time = c.time
			WHERE to_timestamp(%s) <= c.time AND c.time <= to_timestamp(%s)
			ORDER BY c.time''', [exp_id, ch_id, t_from, t_to]).fetchall()
	if len(res) < 1:
		return None, None
	all_data = np.array(res, 'f8')
	data = { f: all_data[:,i] for i, f in enumerate(fields) }

	time_of_day = (data['time'] + HOUR / 2) % DAY
	phi = 2 * np.pi * (time_of_day / DAY)
	ax_rotated = data['ax'] * np.cos(phi)	   + data['ay'] * np.sin(phi)
	ay_rotated = data['ax'] * np.sin(phi) * -1 + data['ay'] * np.cos(phi)
	data['ax'] = ax_rotated
	data['ay'] = ay_rotated
	return data, corr_info

def compute_coefficients(t_from, t_to, experiment, channel_name):
	data, _ = _select(t_from, t_to, experiment, channel_name)
	if data is None:
		return None

	pres_data, tm_data = data['pressure'], data['t_mass_average']
	mask = np.where(~np.isnan(data['revised']) & ~np.isnan(data['a0']) & ~np.isnan(pres_data) & ~np.isnan(tm_data))
	if not np.any(mask):
		return None

	mean_pres, mean_tm = np.nanmean(pres_data), np.nanmean(tm_data)
	diff_pres, diff_tm = mean_pres - pres_data, mean_tm - tm_data
	series = [diff_pres, diff_tm, data['a0'], data['ax'], data['ay'], data['az']]
	regr_x = np.column_stack([ser[mask] for ser in series])
	regr_y = np.log(data['revised'][mask])

	with_intercept = np.column_stack((np.full(len(regr_x), 1), regr_x))
	ols = sm.OLS(regr_y, with_intercept)
	ols_result = ols.fit()
	print(ols_result.summary())
	names = ['p', 'tm', 'c0', 'cx', 'cy', 'cz']
	return {
		'coef': { name: ols_result.params[i + 1] for i, name in enumerate(names) },
		'error': { name: ols_result.bse[i + 1] for i, name in enumerate(names) },
		'length': np.count_nonzero(mask),
		'mean': {
			'pressure': mean_pres,
			't_mass_average': mean_tm
		}
	}

def select_with_corrected(t_from, t_to, experiment, channel_name, query):
	data, corr_info = _select(t_from, t_to, experiment, channel_name)
	if data is None:
		return [], []

	info = compute_coefficients(t_from, t_to, experiment, channel_name)
	print(info)
	coef = info['coef']

	data['expected'] = (data['a0'] * coef['c0'] + data['az'] * coef['cz'] \
					  + data['ax'] * coef['cx'] + data['ay'] * coef['cy']) * 100
	data['a0'] = data['a0'] * coef['c0'] * 100
	data['axy'] = np.hypot(data['ax'] * coef['cx'], data['ay'] * coef['cy'])

	diff_tm, diff_pres = (info['mean'][i] - data[i] for i in ['t_mass_average', 'pressure'])
	data['corrected'] = data['revised'] * (1 - coef['p'] * diff_pres) * (1 - coef['tm'] * diff_tm)
	
	if 'time' not in query:
		query = ['time'] + query
	fields = [f for f in query if f in data]
	result = np.column_stack([data[f] for f in fields])
	return np.where(np.isnan(result), None, np.round(result, 2)).tolist(), fields

def set_coefficients(req):
	experiment = req['experiment']
	channel = req['channel']
	with pool.connection() as conn:
		info = {
			'coef_p': req.get('coef_p', 0),
			'coef_t': req.get('coef_t', 0),
			'length': req.get('length'),
			'modified': req.get('modified'),
			'time': int(datetime.now().timestamp())
		}
		conn.execute('UPDATE muon.channels SET correction_info = %s WHERE experiment = %s AND name = %s',
			[json.dumps(info), experiment, channel])
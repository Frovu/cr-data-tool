import logging
from database import pool
from muon.database import select
from gsm.expected import get_variation
from sklearn.linear_model import LinearRegression
import numpy as np

log = logging.getLogger('crdt')

def _select(t_from, t_to, experiment, channel_name):
	with pool.connection() as conn:
		lat, lon, corr_info = conn.execute('SELECT lat, lon, correction_info FROM muon.experiments e '+\
			'JOIN muon.channels c ON e.name = c.experiment ' +\
			'WHERE e.name = %s AND c.name = %s', [experiment, channel_name]).fetchone()

	fields = ['original', 'revised', 'pressure', 't_mass_average']
	res = select(t_from, t_to, experiment, channel_name, fields)
	if len(res) < 1:
		raise ValueError('No data')
	all_data = np.array(res, 'f8')
	data = { f: all_data[:,i] for i, f in enumerate(['time'] + fields) }
	time = data['time']

	gsm_q_interval = [max(time[0], t_from), min(time[-1], t_to)]
	gsm_time, gsm_var_unaligned = get_variation(gsm_q_interval, lat, lon, channel_name)
	data['expected'] = np.full(len(time), np.nan, 'f8')
	data['expected'][np.in1d(time, gsm_time)] = gsm_var_unaligned
	return data, corr_info

def compute_coefficients(t_from, t_to, experiment, channel_name, rich=False):
	data, _ = _select(t_from, t_to, experiment, channel_name)

	pres_data, tm_data, gsm_var = data['pressure'], data['t_mass_average'], data['expected']
	mask = np.where(~np.isnan(data['revised']) & ~np.isnan(gsm_var) & ~np.isnan(pres_data) & ~np.isnan(tm_data))
	if not np.any(mask):
		return (0, 0, 0, 0) if rich else (0, 0)

	mean_pres, mean_tm = np.nanmean(pres_data), np.nanmean(tm_data)
	diff_pres, diff_tm = mean_pres - pres_data, mean_tm - tm_data
	regr_data = np.column_stack((diff_pres[mask], diff_tm[mask], gsm_var[mask]))
	regr = LinearRegression().fit(regr_data, np.log(data['revised'][mask]))
	coef_p, coef_t, coef_v = regr.coef_
	return (coef_p, coef_t) if not rich else (coef_p, coef_t, coef_v, np.count_nonzero(mask))

def select_with_corrected(t_from, t_to, experiment, channel_name, query):
	data, corr_info = _select(t_from, t_to, experiment, channel_name)

	if corr_info is None:
		coef_pres, coef_tm = compute_coefficients(t_from, t_to, experiment, channel_name)
		log.warning('Muon: correction coefs not set for %s:%s', experiment, channel_name)
	else:
		coef_pres, coef_tm = [corr_info[i] for i in ['coef_p', 'coef_t']]

	diff_tm, diff_pres = (np.nanmean(data[i]) - data[i] for i in ['t_mass_average', 'pressure'])
	data['corrected'] = data['revised'] * np.exp(-1 * coef_pres * diff_pres) * (1 - coef_tm * diff_tm)
	
	if 'time' not in query:
		query = ['time'] + query
	fields = [f for f in query if f in data]
	result = np.column_stack([data[f] for f in fields])
	return np.where(np.isnan(result), None, np.round(result, 2)).tolist(), fields

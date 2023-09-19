from datetime import datetime
from database import pool, upsert_many
from muon.database import select
from gsm.expected import get_variation
from sklearn.linear_model import LinearRegression
import numpy as np

def get_predicted(t_from, t_to, experiment, channel_name):
	with pool.connection() as conn:
		lat, lon = conn.execute('SELECT lat, lon FROM muon.experiments WHERE name = %s', [experiment]).fetchone()
	time, var = get_variation((t_from, t_to), lat, lon, channel_name)
	return np.column_stack((time, np.where(np.isnan(var), None, var))).tolist() if var is not None else []

def do_compute(t_from, t_to, experiment, channel_name):
	with pool.connection() as conn:
		ch_id, lat, lon = conn.execute('SELECT c.id, lat, lon FROM muon.experiments e '+\
			'JOIN muon.channels c ON e.name = c.experiment ' +\
			'WHERE e.name = %s AND c.name = %s', [experiment, channel_name]).fetchone()

		res = select(t_from, t_to, experiment, channel_name, ['revised', 'pressure', 't_mass_average'])[0]
		if len(res) < 1:
			raise ValueError('No data')
		data = np.array(res, 'f8')
		time, raw_counts, pres_data, tm_data = [data[:,i] for i in range(4)]

		gsm_q_interval = [max(time[0], t_from), min(time[-1], t_to)]
		gsm_time, gsm_var_unaligned = get_variation(gsm_q_interval, lat, lon, channel_name)
		gsm_var = np.full(len(data), np.nan, 'f8')
		gsm_var[np.in1d(time, gsm_time)] = gsm_var_unaligned

		mask = np.where(~np.isnan(raw_counts) & ~np.isnan(gsm_var) & ~np.isnan(pres_data) & ~np.isnan(tm_data))

		mean_pres, mean_tm = np.nanmean(pres_data), np.nanmean(tm_data)
		diff_pres, diff_tm = mean_pres - pres_data, mean_tm - tm_data
		regr_data = np.column_stack((diff_pres[mask], diff_tm[mask], gsm_var[mask]))
		regr = LinearRegression().fit(regr_data, np.log(raw_counts[mask]))
		coef_pr, coef_tm, coef_v = regr.coef_
		print(coef_pr, coef_tm, coef_v)

		corrected = raw_counts * np.exp(-1 * coef_pr * diff_pres) * (1 - coef_tm * diff_tm)

		corrected = np.where(np.isnan(corrected), None, np.round(corrected, 2))
		time = np.array([datetime.utcfromtimestamp(t) for t in time])
		result = np.column_stack((time, corrected)).tolist()

		upsert_many(conn, 'muon.counts_data', ['channel', 'time', 'corrected'],
			result, constants=[ch_id], conflict_constraint='time, channel', write_nulls=True)
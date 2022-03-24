import data_source.gsm.expected as gsm
import data_source.muones.db_proxy as proxy
import data_source.muones.obtain_data as parser
import data_source.temperature_model.temperature as temperature
import logging
import numpy as np
from scipy import interpolate, stats
from sklearn.linear_model import LinearRegression
import time
import re
from math import floor, ceil

COLUMN_TEMP = 'T_m'
MODEL_PERIOD = 3600

def _calculate_temperatures(channel, t_from, t_to, merge_query):
    lat, lon = channel.coordinates
    pa_from, pa_to = floor(t_from/MODEL_PERIOD)*MODEL_PERIOD, ceil(t_to/MODEL_PERIOD)*MODEL_PERIOD
    logging.debug(f'Muones: querying model temp ({lat}, {lon}) {t_from}:{t_to}')
    delay = .1
    while True:
        status, data = temperature.get(lat, lon, pa_from, pa_to, only=['mass_average'], merge_query=merge_query)
        if status == 'accepted':
            merge_query(data)
        elif status in ['failed', 'unknown']:
            raise Exception('Muones: failed to obtain T_m: '+status)
        elif status == 'ok':
            logging.debug(f'Muones: got model response {pa_from}:{pa_to}')
            data = np.array(data[0])
            times = data[:,0]
            t_avg = data[:,1]
            if channel.period != MODEL_PERIOD:
                interp = interpolate.interp1d(times, t_avg, axis=0)
                times = np.arange(t_from, t_to+1, channel.period)
                t_avg = interp(times)
            return np.column_stack((times, t_avg))
        delay += .1 if delay < 1 else 0
        time.sleep(delay)

def get_prepare_tasks(channel, fill_fn, subquery_fn):
        tasks = []
        tasks.append(('raw counts', fill_fn, (
            lambda i: proxy.analyze_integrity(channel, i, 'source'),
            lambda i: proxy.upsert(channel, *parser.obtain(channel, *i, 'source')),
            False, 1, 365*24
        )))
        tasks.append(('pressure', fill_fn, (
            lambda i: proxy.analyze_integrity(channel, i, 'pressure'),
            lambda i: proxy.upsert(channel, *parser.obtain(channel, *i, 'pressure')),
            False, 1, 365*24
        )))
        tasks.append(('temperature-model', fill_fn, (
            lambda i: proxy.analyze_integrity(channel, i, COLUMN_TEMP),
            lambda i: proxy.upsert(channel, _calculate_temperatures(channel, *i, subquery_fn), COLUMN_TEMP, epoch=True),
            True, 8, 365*24
        )))
        return tasks

def corrected(channel, interval, recalc):
    is_p_corrected = channel.station_name in [] # FIXME:
    columns = ['source', 'T_m'] + ([] if is_p_corrected else ['pressure'])
    where = ' AND '.join([f'{c} > 0' for c in columns])
    data = np.array(proxy.select(channel, interval, columns, where=where)[0], dtype=np.float64)
    if len(data) < 32:
        return None
    interval_len = interval[1]-interval[0]
    coef_recalc = recalc or not channel.coef_tm or not channel.coef_len or channel.coef_len < interval_len

    time, raw, tm_src, pr_src = data[:,0], data[:,1], data[:,2], data[:,3]
    tm, pr = (np.mean(tm_src) - tm_src), (np.mean(pr_src) - pr_src)
    gsm_result = np.column_stack(gsm.get_variation(channel, interval))
    with_v = None not in gsm_result
    v_gsm = with_v and gsm_result[np.in1d(gsm_result[:,0], time),1:]
    v_isotropic, v_anisotropic = with_v and v_gsm[:,0], with_v and v_gsm[:,1]
    if coef_recalc:
        regr_data = np.column_stack((pr, tm, v_isotropic, v_anisotropic+1) if with_v else (pr, tm))
        regr = LinearRegression().fit(regr_data, np.log(raw))
        coef_pr, coef_tm, coef_v0, coef_v1 = regr.coef_ if with_v else (*regr.coef_, 0, 0)
        channel.update_coefs(coef_pr, coef_tm, interval_len)
        logging.debug(f'Muon coef: {channel.station_name}/{channel.name} = {regr.coef_}')
    else:
        coef_pr, coef_tm, coef_v0, coef_v1 = channel.coef_pr, channel.coef_tm, 0, 0
    corrected = raw * np.exp(-1 * coef_pr * pr) * (1 - coef_tm * tm)
    corrected_v = with_v and raw * np.exp(-1 * coef_pr * pr) * (1 - coef_tm * tm) \
        / (1 + coef_v0 * v_isotropic) / (1 + coef_v1 * v_anisotropic)
    print(v_isotropic[:10])
    print(v_anisotropic[:10])

    v_expected = v_isotropic + v_anisotropic
    # FIXME: proxy.upsert(channel, np.column_stack((time, corrected)), 'corrected', epoch=True)
    result = [time, corrected, raw, pr_src, tm_src] + ([corrected_v, v_expected] if with_v else [])
    fields = ['time', 'corrected', 'source', 'pressure', 'T_m'] + (['corrected_v', 'v_expected'] if with_v else [])
    return np.column_stack(result).tolist(), fields, {
        'coef_pressure': coef_pr,
        'coef_temperature': coef_tm,
        'coef_variation': coef_v1,
        'coef_per_length': interval_len if coef_recalc else channel.coef_len
    }

def calc_coefs(channel, interval):
    columns = ['source', 'T_m', 'pressure']
    where = ' AND '.join([f'{c} > 0' for c in columns])
    data = np.array(proxy.select(channel, interval, columns, where=where)[0], dtype=np.float64)
    if len(data) < 32:
        return {}
    time, raw, tm_src, pr_src = data[:,0], data[:,1], data[:,2], data[:,3]
    tm, pr = (np.mean(tm_src) - tm_src), (np.mean(pr_src) - pr_src)
    gsm_r = np.column_stack(gsm.get_variation(channel, interval))
    v_exp = gsm_r[np.in1d(gsm_r[:,0], time),1]
    regr = LinearRegression().fit(np.column_stack((pr, tm, v_exp)), np.log(raw))
    coef_pr, coef_tm, coef_v = regr.coef_
    return {
        'coef_pressure': coef_pr,
        'coef_temperature': coef_tm,
        'coef_variation': coef_v
    }

def calc_correlation(data, fields, only):
    data = np.array(data, dtype=np.float)
    x, y = data[:,0], data[:,1]
    variation = y / np.mean(y) * 100 - 100
    lg = stats.linregress(x, variation)
    rrange = np.linspace(x[0], x[-1])
    return {
        'slope': lg.slope,
        'error': lg.stderr,
        'x': np.round(x, 4).tolist(),
        'y': np.round(variation, 4).tolist(),
        'rx': rrange.tolist(),
        'ry': (lg.intercept + lg.slope * rrange).tolist()
    } if only != 'coef' else {
        'coef': lg.slope,
        'error': lg.stderr
    }

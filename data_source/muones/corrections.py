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
    if not coef_recalc:
        coef_pr, coef_tm = channel.coef_pr, channel.coef_tm
    else:
        logging.debug(f'Muones: recalc coefs {channel.station_name}/{channel.name} <{interval_len}')
    time, raw, tm = data[:,0], data[:,1], data[:,2]
    tm = (np.mean(tm) - tm)
    if is_p_corrected:
        if coef_recalc:
            lg = stats.linregress(tm, np.log(raw))
            coef_pr, coef_tm = None, lg.slope
        corrected = raw * (1 - coef_tm * tm)
    else:
        pr = data[:,3]
        pr = (np.mean(pr) - pr)
        if coef_recalc:
            regr_data = np.column_stack((pr, tm))
            regr = LinearRegression().fit(regr_data, np.log(raw))
            coef_pr, coef_tm = regr.coef_
        corrected = raw * np.exp(-1 * coef_pr * pr) * (1 - coef_tm * tm)
    proxy.upsert(channel, np.column_stack((time, corrected)), 'corrected', epoch=True)
    if coef_recalc:
        channel.update_coefs(coef_pr, coef_tm, interval_len)
    res = proxy.select(channel, interval, ['corrected'] + columns, where='source > 0')
    return *res, {
        'coef_pressure': coef_pr,
        'coef_temperature': coef_tm,
        'coef_per_length': interval_len if coef_recalc else channel.coef_len
    }

def multiple_regression(data):
    return LinearRegression().fit(data[:,1:], np.log(data[:,0]))

def calc_correlation(data, fields):
    data = np.array(data, dtype=np.float)
    x, y = data[:,0], data[:,1]
    variation = y / np.mean(y) * 100 - 100
    lg = stats.linregress(x, variation)
    rrange = np.linspace(x[0], x[-1])
    return {
        'slope': lg.slope,
        'error': lg.stderr,
        'x': x.tolist(),
        'y': variation.tolist(),
        'rx': rrange.tolist(),
        'ry': (lg.intercept + lg.slope * rrange).tolist()
    }

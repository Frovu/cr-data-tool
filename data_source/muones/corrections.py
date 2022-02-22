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

def _calculate_temperatures(lat, lon, t_from, t_to, period, add_query):
    pa_from, pa_to = floor(t_from/MODEL_PERIOD)*MODEL_PERIOD, ceil(t_to/MODEL_PERIOD)*MODEL_PERIOD
    logging.debug(f'Muones: querying model temp ({lat}, {lon}) {t_from}:{t_to}')
    delay = .1
    while True:
        status, data = temperature.get(lat, lon, pa_from, pa_to, only=['mass_average'])
        if status == 'accepted':
            add_query(data)
        elif status == 'failed':
            raise Exception('Muones: failed to obtain T_m')
        elif status == 'ok':
            logging.debug(f'Muones: got model response')
            data = np.array(data[0])
            times = data[:,0]
            t_avg = data[:,1]
            if period != MODEL_PERIOD:
                interp = interpolate.interp1d(times, t_avg, axis=0)
                times = np.arange(t_from, t_to+1, period)
                t_avg = interp(times)
            return np.column_stack((times, t_avg))
        delay += .1 if delay < 1 else 0
        time.sleep(delay)

def get_prepare_tasks(station, period, channel, fill_fn, subquery_fn):
        lat, lon = proxy.coordinates(station)
        tasks = []
        tasks.append(('raw data', fill_fn, (
            lambda i: proxy.analyze_integrity(station, *i, period, 'raw_acc_cnt'),
            lambda i: proxy.upsert(station, period, channel, *parser.obtain(station, *i, period, channel)),
            False, 4, 7200
        )))
        tasks.append(('air temperature', fill_fn, (
            lambda i: proxy.analyze_integrity(station, *i, period, COLUMN_TEMP),
            lambda i: proxy.upsert(station, period, channel, _calculate_temperatures(lat, lon, *i, period, subquery_fn), ['time', COLUMN_TEMP], epoch=True),
            True
        )))
        return tasks

# !!! Presumes that all needed data is prepared
def correct(*args):
    station, t_from, t_to, period = args
    data = np.array(proxy.select(*args, ['n_v_raw', 'pressure', 'T_m'])[0], dtype=np.float64)
    data = data[~np.isnan(data[:,1])]
    data = data[~np.isnan(data[:,2])]
    n_u, p, t = data[:,1], data[:,2], data[:,3]
    p = (np.mean(p) - p)
    t = (np.mean(t) - t)
    regr = multiple_regression(np.column_stack((n_u, p, t)))
    print(regr)
    beta, alpha = regr.coef_
    n_c = n_u * np.exp(-1 * beta * p) * (1 - alpha * t)
    proxy.upsert(station, period, channel, np.column_stack((data[:,0], n_c)), ['time', 'n_v'], epoch=True)
    res = proxy.select(station, t_from, t_to, period, ['n_v_raw', 'n_v', 'pressure', 'T_m'], where='n_v_raw > 99')
    return *res, {"a": alpha, "b": beta}

def multiple_regression(data):
    data = data[data[:,0] > 0]
    return LinearRegression().fit(data[:,1:], np.log(data[:,0]))

def calc_correlation(data, fields):
    data = np.array(data, dtype=np.float)
    yavg = np.nanmean(data[:,1])
    filter = int(yavg - yavg/4)
    was = data.shape
    data = data[np.where(data[:,1] > filter)]
    logging.debug(f'Muones: correlation to {fields[0]} filtered: {was[0]-data.shape[0]}/{was[0]}')
    x, y = data[:,0], data[:,1]
    lg = stats.linregress(x, y)
    rrange = np.linspace(x[0], x[-1])
    return {
        'r': lg.rvalue,
        'x': x.tolist(),
        'y': y.tolist(),
        'rx': rrange.tolist(),
        'ry': (lg.intercept + lg.slope * rrange).tolist()
    }

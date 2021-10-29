import data_source.muones.db_proxy as proxy
import data_source.muones.obtain_data as parser
import data_source.temperature_model.temperature as temperature
import logging
import numpy as np
from scipy import interpolate, stats
import time
import re
from math import floor, ceil

COLUMNS_TEMP = ['T_m']
COLUMNS_RAW = ['raw_acc_cnt', 'n_v_raw', 'pressure']
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

def get_prepare_tasks(station, period, fill_fn, subquery_fn, against):
        lat, lon = proxy.coordinates(station)
        tasks = []
        tasks.append(('raw data', fill_fn, (
            lambda i: proxy.analyze_integrity(station, i[0], i[1], period, COLUMNS_RAW[0]),
            lambda i: proxy.upsert(station, period, parser.obtain(station, period, i[0], i[1]), COLUMNS_RAW),
            True
        )))
        if against == 'T_m':
            tasks.append(('temp mass-avg', fill_fn, (
                lambda i: proxy.analyze_integrity(station, i[0], i[1], period, COLUMNS_TEMP[0]),
                lambda i: proxy.upsert(station, period, _calculate_temperatures(lat, lon, i[0], i[1], period, subquery_fn), COLUMNS_TEMP, True),
                True
            )))
        return tasks

def correct(t_from, t_to, station, period):
    prepare_data(station, t_from, t_to, period)

def linregress_corr(data, fields):
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

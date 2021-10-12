import data_source.muones.db_proxy as proxy
import data_source.muones.obtain_data as parser
import data_source.temperature_model.temperature as temperature
import logging
import numpy as np
from scipy import interpolate
import time
import re
from math import floor, ceil

BATCH_SIZE = 4096
COLUMNS_TEMP = ['T_m']
COLUMNS_RAW = ['raw_acc_cnt', 'n_v_raw', 'pressure']
MODEL_PERIOD = 3600

def _T_m(ts, levels):
    diff = np.abs(np.diff(levels))
    return np.sum([np.mean([ts[i],ts[i+1]])*diff[i]/1000 for i in range(diff.shape[0])])

def _calculate_temperatures(lat, lon, t_from, t_to, period):
    pa_from, pa_to = floor(t_from/MODEL_PERIOD)*MODEL_PERIOD, ceil(t_to/MODEL_PERIOD)*MODEL_PERIOD
    logging.debug(f'Muones: querying model temp ({lat}, {lon}) {t_from}:{t_to}')
    delay = .1
    while True:
        status, data = temperature.get_by_epoch(lat, lon, pa_from, pa_to)
        if status == 'ok':
            logging.debug(f'Muones: got model response')
            levels = [float(re.match(r't_(\d+)mb', f).group(1)) for f in data[1] if re.match(r't_(\d+)mb', f)]
            data = np.array(data[0])
            times = data[:,0]
            values = data[:,1:]
            if period != MODEL_PERIOD:
                interp = interpolate.interp1d(times, values, axis=0)
                times = np.arange(t_from, t_to+1, period)
                values = interp(times)
            result = np.array([_T_m(temps, levels) for temps in values])
            return np.array([times.astype(int), result]).T
        delay += .1 if delay < 1 else 0
        time.sleep(delay)

def get_prepare_tasks(station, period, fill_fn):
        lat, lon = proxy.coordinates(station)
        t_fn = (
            lambda i: proxy.analyze_integrity(station, i[0], i[1], period, COLUMNS_TEMP[0]),
            lambda i: proxy.upsert(station, period, _calculate_temperatures(lat, lon, i[0], i[1], period), COLUMNS_TEMP, True)
        )
        r_fn = (
            lambda i: proxy.analyze_integrity(station, i[0], i[1], period, COLUMNS_RAW[0]),
            lambda i: proxy.upsert(station, period, parser.obtain(station, period, i[0], i[1]), COLUMNS_RAW)
        )
        return [
            ('temp mass-avg', fill_fn, (*t_fn, True)),
            ('raw data', fill_fn, r_fn)
        ]

def correct(t_from, t_to, station, period):
    prepare_data(station, t_from, t_to, period)

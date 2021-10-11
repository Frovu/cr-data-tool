import data_source.muones.db_proxy as proxy
import data_source.muones.obtain_data as parser
import data_source.temperature_model.temperature as temperature
import logging
import numpy as np
from scipy import interpolate
import time
import re
import traceback
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

def _prepare(station, t_from, t_to, period, integrity_column, process_fn):
    missing = proxy.analyze_integrity(station, t_from, t_to, period, integrity_column)
    for interval in missing:
        batch = period*BATCH_SIZE
        for i_start in range(interval[0], interval[1], batch):
            i_end = i_start+batch if i_start+batch < interval[1] else interval[1]
            process_fn(i_start, i_end)

def prepare_data(t_from, t_to, station, period):
    try:
        lat, lon = proxy.coordinates(station)
        _prepare(station, t_from, t_to, period, COLUMNS_TEMP[0],
            lambda a, b: proxy.upsert(station, period, _calculate_temperatures(lat, lon, a, b, period), COLUMNS_TEMP, True))
        _prepare(station, t_from, t_to, period, COLUMNS_RAW[0],
            lambda a, b: proxy.upsert(station, period, parser.obtain(station, period, a, b), COLUMNS_RAW))
    except Exception:
        logging.error(f'Muones: failed to prepare: {traceback.format_exc()}')

def correct(t_from, t_to, station, period):
    prepare_data(station, t_from, t_to, period)

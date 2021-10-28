from core.sequence_filler import SequenceFiller, fill_fn
import numpy as np
from scipy import interpolate, ndimage
import data_source.temperature_model.parser as parser
import data_source.temperature_model.proxy as proxy
from math import floor, ceil
import logging as log

HOUR = 3600
MODEL_PERIOD = HOUR * 6
MODEL_EPOCH = np.datetime64('1948-01-01').astype(int)
SPLINE_INDENT = 2 # additional periods on edges for spline evaluation
SPLINE_INDENT_H = MODEL_PERIOD // HOUR * SPLINE_INDENT
scheduler = SequenceFiller(ttl=0)

# transform geographical coords to index coords
def _get_coords(lat, lon):
    lat_i = interpolate.interp1d([90, -90], [0, 72])
    lon_i = interpolate.interp1d([0, 360], [0, 144]) # we will get out of range at lat > 175.5 but I hope its not critical
    return [[lat_i(lat)], [lon_i((lon + 360) % 360)]] # lon: [-180;180]->[0;360]

def _approximate_for_point(data, lat, lon):
    coords = _get_coords(lat, lon)
    approximated = np.empty(data.shape[:2])
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            approximated[i][j] = ndimage.map_coordinates(data[i][j], coords, order=3, mode='nearest')
    return approximated

# 6h model resolution -> 1h resolution
def _interpolate_time(times, data):
    new_times = np.arange(times[0], times[-1] + HOUR, HOUR)
    result = np.empty((new_times.shape[0], data.shape[1]))
    for level_col in range(data.shape[1]): # interpolate each level separately
        old_line = data[:,level_col]
        spline = interpolate.splrep(times, old_line, s=0)
        result[:,level_col] = interpolate.splev(new_times, spline)
    return new_times, result

def _t_mass_average(data):
    diff = np.abs(np.diff(proxy.LEVELS)) / np.max(proxy.LEVELS)
    return np.array([np.sum(diff * ((x[:-1] + x[1:]) / 2)) for x in data])

def _fill_interval(interval, lat, lon, mq):
    t_from = MODEL_PERIOD * (floor(interval[0] / MODEL_PERIOD) - SPLINE_INDENT)
    t_to   = MODEL_PERIOD * ( ceil(interval[1] / MODEL_PERIOD) + SPLINE_INDENT)
    log.info(f"NCEP: Obtaining ({lat},{lon}) {t_from}:{t_to}")
    times_6h, data = parser.obtain(t_from, t_to, mq)
    log.debug(f"NCEP: Retrieved [{data.shape[0]}] ({lat},{lon}) {t_from}:{t_to}")
    approximated = _approximate_for_point(data, lat, lon)
    log.debug(f"NCEP: Approximated ({lat},{lon}) {t_from}:{t_to}")
    times_1h, result = _interpolate_time(times_6h, approximated)
    log.debug(f"NCEP: Interpolated [{result.shape[0]}] ({lat},{lon}) {t_from}:{t_to}")
    t_m = _t_mass_average(result)
    log.debug(f"NCEP: T_m [{t_m.shape[0]}] ({lat},{lon}) {t_from}:{t_to}")
    result_m = np.column_stack((times_1h, t_m, result))
    slice = SPLINE_INDENT_H # do not insert edges of spline
    proxy.insert(lat, lon, result_m[slice:(-1*slice)])

def _bound_query(t_from, t_to):
    t_from = MODEL_PERIOD * floor(t_from / MODEL_PERIOD)
    t_to   = MODEL_PERIOD *  ceil(t_to   / MODEL_PERIOD)
    now    = MODEL_PERIOD * floor(np.datetime64('now').astype(int) / MODEL_PERIOD)
    end_trim = now - MODEL_PERIOD * (SPLINE_INDENT + 4) # FIXME: when real time functionality arrives
    if t_from < MODEL_EPOCH: t_from = MODEL_EPOCH
    if t_to > end_trim: t_to = end_trim
    return t_from, t_to

def get_stations():
    return proxy.get_stations()

def get(lat, lon, t_from, t_to, no_response=False):
    lat = round(float(lat), 2)
    lon = round(float(lon), 2)
    if not proxy.get_station(lat, lon):
        return 'unknown', None
    t_from, t_to = _bound_query(t_from, t_to)
    token = (lat, lon)
    done, info = scheduler.status((token, t_from, t_to))
    if done == False:
        return 'failed' if info.get('failed') else 'busy', info
    if done or not proxy.analyze_integrity(lat, lon, t_from, t_to):
        return 'ok', None if no_response else proxy.select(lat, lon, t_from, t_to)
    log.info(f'NCEP: Filling ({lat}, {lon}) {t_from}:{t_to}')
    mq_fn = lambda q: scheduler.merge_query(token, t_from, t_to, q)
    query = scheduler.do_fill(token, t_from, t_to, HOUR, [
        ('temperature-model', fill_fn, (
            lambda i: proxy.analyze_integrity(lat, lon, i[0], i[1]),
            lambda i: _fill_interval(i, lat, lon, mq_fn),
            True, 16 # multithreading, workers=16
        ))
    ])
    return 'accepted', query

from core.sequence_filler import SequenceFiller, fill_fn
import numpy as np
from scipy import interpolate, ndimage
import data_source.atmosphere.parser as parser
import data_source.atmosphere.proxy as proxy
import data_source.atmosphere.gfs_parser as gfs
from math import floor, ceil
import logging as log
LEVELS = proxy.LEVELS
scheduler = SequenceFiller(ttl=0)

HOUR = 3600
MODEL_PERIOD = 6 * HOUR
FORECAST_ALLOW_FUTURE = 3 * 24 * HOUR
MODEL_EPOCH = np.datetime64('1948-01-01').astype(int)
SPLINE_INDENT = 1 # additional periods on edges for spline evaluation
SPLINE_INDENT_H = MODEL_PERIOD // HOUR * SPLINE_INDENT
MODEL_LAG = MODEL_PERIOD * (10 + SPLINE_INDENT)

# transform geographical coords to index coords
def _get_coords(lat, lon, resolution):
    lat_i = interpolate.interp1d([90, -90], [0, 180 // resolution])
    lon_i = interpolate.interp1d([0,  360], [0, 360 // resolution])
    return [[lat_i(lat)], [lon_i((lon + 360) % 360)]] # lon: [-180;180]->[0;360]

def _approximate_for_point(data, lat, lon, resolution=2.5):
    coords = _get_coords(lat, lon, resolution)
    approximated = np.empty(data.shape[:2])
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            approximated[i][j] = ndimage.map_coordinates(data[i][j], coords, mode='wrap')
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
    diff = np.abs(np.diff(LEVELS)) / np.max(LEVELS)
    return np.array([np.sum(diff * ((x[:-1] + x[1:]) / 2)) for x in data])

def _fill_interval(interval, lat, lon, mq):
    indent = SPLINE_INDENT if (interval[1]-interval[0] > HOUR*6) else SPLINE_INDENT*2
    t_from = MODEL_PERIOD * (floor(interval[0] / MODEL_PERIOD) - indent)
    t_to   = MODEL_PERIOD * ( ceil(interval[1] / MODEL_PERIOD) + indent)
    log.info(f"NCEP/NCAR: Obtaining ({lat},{lon}) {t_from}:{t_to}")
    times_6h, data = parser.obtain('temperature', t_from, t_to, mq)
    log.debug(f"NCEP/NCAR: Retrieved [{data.shape[0]}] ({lat},{lon}) {t_from}:{t_to}")
    approximated = _approximate_for_point(data, lat, lon)
    log.debug(f"NCEP/NCAR: Approximated ({lat},{lon}) {t_from}:{t_to}")
    times_1h, result = _interpolate_time(times_6h, approximated)
    log.debug(f"NCEP/NCAR: Interpolated [{result.shape[0]}] ({lat},{lon}) {t_from}:{t_to}")
    t_m = _t_mass_average(result)
    log.debug(f"NCEP/NCAR: T_m [{t_m.shape[0]}] ({lat},{lon}) {t_from}:{t_to}")
    slice = SPLINE_INDENT_H # do not insert edges of spline
    result_m = np.column_stack((times_1h, t_m, result))[slice:(-1*slice)]
    proxy.insert(lat, lon, result_m)
    model_data_end = int(result_m[-1][0]) + HOUR
    if model_data_end < interval[1]:
        lag = (interval[1] - model_data_end) // 3600 + 1
        log.warning(f"NCEP/NCAR: Model lag exceeds by {lag} hours, using forecast")
        _fill_with_forecast([0, 1], model_data_end, interval[1], lat, lon)

def _fill_with_forecast(progress, t_from, t_to, lat, lon):
    data = gfs.obtain(lat, lon, t_from, t_to, progress)
    log.debug(f"GFS: Complete [{data.shape[0]}] ({lat},{lon}) {t_from}:{t_to}")
    t_m = _t_mass_average(data[:,2:])
    log.debug(f"GFS: T_m [{t_m.shape[0]}] ({lat},{lon}) {t_from}:{t_to}")
    data = np.insert(data, 2, t_m, axis=1)
    proxy.insert(lat, lon, data, forecast=True)

def _bound_query(t_from, t_to):
    t_from = MODEL_PERIOD * floor(t_from / MODEL_PERIOD)
    t_to   = MODEL_PERIOD *  ceil(t_to   / MODEL_PERIOD)
    now    = MODEL_PERIOD * floor(np.datetime64('now').astype(int) / MODEL_PERIOD)
    end_trim = now + FORECAST_ALLOW_FUTURE
    if t_from - MODEL_PERIOD * SPLINE_INDENT < MODEL_EPOCH: t_from = MODEL_EPOCH
    if t_to > end_trim: t_to = end_trim
    model_end = parser.get_hopeless() or now - MODEL_LAG
    forecast_from = model_end + HOUR if model_end < t_to else None
    if forecast_from and forecast_from < t_from: forecast_from = t_from
    return t_from, t_to, forecast_from

def get(lat, lon, t_from, t_to, no_response=False, only=[], merge_query=None):
    lat = round(float(lat), 2)
    lon = round(float(lon), 2)
    if not proxy.get_station(lat, lon):
        return 'unknown', None
    t_from, t_to, forecast_from = _bound_query(t_from, t_to)
    token = (lat, lon)
    done, info = scheduler.status((token, t_from, t_to))
    if done == False:
        return 'failed' if info.get('failed') else 'busy', info
    model_t_to = forecast_from - HOUR if forecast_from else t_to
    model_required = proxy.analyze_integrity(lat, lon, t_from, model_t_to)
    forecast_required = forecast_from and proxy.analyze_integrity(lat, lon, forecast_from, t_to)
    if done or (not model_required and not forecast_required):
        return 'ok', None if no_response else proxy.select(lat, lon, t_from, t_to, only)
    query = None
    if model_required:
        log.info(f'NCEP/NCAR: Filling ({lat}, {lon}) {t_from}:{model_t_to}')
        mq_fn = merge_query or (lambda q: scheduler.merge_query(token, t_from, t_to, q))
        query = scheduler.do_fill(token, t_from, model_t_to, HOUR, [
            ('temperature-model', fill_fn, (
                lambda i: proxy.analyze_integrity(lat, lon, i[0], i[1]),
                lambda i: _fill_interval(i, lat, lon, mq_fn),
                True, 16 # multithreading, workers=16
            ))
        ], key_overwrite=(token, t_from, t_to))
    if forecast_required:
        joined_interv = (forecast_required[0][0], forecast_required[-1][1])
        log.info(f'GFS: Filling ({lat}, {lon}) {joined_interv[0]}:{joined_interv[1]}')
        tasks = [(_fill_with_forecast, (*joined_interv, lat, lon), 'temperature-forecast', True)]
        query = query or scheduler.query_tasks((token, t_from, t_to), [])
        query.submit_tasks(tasks)
    return 'accepted', query

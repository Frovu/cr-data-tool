import data_source.atmosphere.temperature as temp
import data_source.atmosphere.parser as parser
from math import floor, ceil
from scipy import interpolate
import numpy as np, logging as log

MODEL_PERIOD = 6 * 3600
MODEL_LAG = 20
SPLINE_INDENT = 1

def _bound(t_from, t_to):
    t_from = MODEL_PERIOD * floor(t_from / MODEL_PERIOD) - MODEL_PERIOD
    t_to   = MODEL_PERIOD *  ceil(t_to   / MODEL_PERIOD) + MODEL_PERIOD
    now    = MODEL_PERIOD * floor(np.datetime64('now').astype(int) / MODEL_PERIOD)
    end_trim = now - MODEL_PERIOD * MODEL_LAG
    if t_to > end_trim: t_to = end_trim
    return t_from, t_to

def get(lat, lon, t_from, t_to):
    # TODO: sql proxy
    # TODO: non-blocking
    t_from, t_to = _bound(t_from, t_to)
    log.info(f"gflux: Obtaining ({lat},{lon}) {t_from}:{t_to}")
    times_6h, data = parser.obtain('gflux', t_from, t_to)
    approximated = np.array([d[20][75] for d in data]) # FIXME
    approximated = np.where(np.isnan(approximated), 0, approximated)
    times_1h = np.arange(times_6h[0], times_6h[-1] + 1, 3600)
    spline = interpolate.splrep(times_6h, approximated, s=1)
    result = interpolate.splev(times_1h, spline)
    # return np.column_stack((times_1h, result))
    return np.column_stack((times_6h, approximated))

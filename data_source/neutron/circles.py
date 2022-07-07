from data_source.neutron import database
from scipy import optimize
import numpy as np
import warnings

BASE_LENGTH_H = 24

RING = dict({
    'APTY': 73.05,
    'DRBS': 65.17,
    'FSMT': 293.07,
    'INVK': 234.85,
    'IRKT': 163.58,
    'KERG': 89.71,

    'KIEL2': 65.34,
    'NAIN': 18.32,
    'NEWK': 331.49,
    'NRLK': 124.48,
    'OULU': 67.42,
    'PWNK': 349.56,
    'YKTK': 174.02
})

def _get_direction(station):
    return RING[station]

def _determine_base(data):
    b_len = BASE_LENGTH_H
    time, data = data[:,0], data[:,1:]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        mean_val = np.nanmean(data, axis=0)
        mean_var = np.nanmean(data / mean_val, axis=1)
        indices = np.where(mean_var[:-1*b_len] > 1)[0]
        deviations = np.array([np.std(data[i:i+b_len], 0) for i in indices])
        mean_std = 1 / np.nanmean(deviations, axis=1)
    weightened_std = mean_std * (mean_var[indices] - 1)
    base_idx = indices[np.argmax(weightened_std)]
    return base_idx, base_idx + b_len

def _filter(full_data):
    time, data = full_data[:,0], full_data[:,1:]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        variation = data / np.nanmean(data, axis=0) * 100 - 100
        mean_variation = np.nanmedian(variation, axis=1)
    deviation = variation - mean_variation[:,None]
    mask = np.where((deviation > 3) | (deviation < -7.5)) # meh values
    data[mask] = np.nan
    excluded = list()
    for station_i in range(data.shape[1]): # exclude station if >10 spikes
        if len(np.where(mask[1] == station_i)[0]) > 10:
            data[:,station_i] = np.nan
            excluded.append(station_i)
    filtered = np.count_nonzero(~np.isin(mask[1], excluded))
    return full_data, filtered, excluded

def anisotropy_fn(x, a, scale, sx, sy):
    return np.cos(x * a * np.pi / 180 + sx) * scale + sy

def precursor_idx(x, y, amp_cutoff = 1, details = False):
    amax, amin = x[np.argmax(y)], x[np.argmin(y)]
    approx_dist = np.abs(amax - amin)
    center_target = 180 if approx_dist < 180 else 360
    shift = center_target - (amax + amin) / 2
    x = (x + shift + 360) % 360
    bounds = (approx_dist if approx_dist > 180 else (360-approx_dist)) / 6
    trim = np.where((x > bounds) & (x < 360-bounds))
    try:
        popt, pcov = optimize.curve_fit(anisotropy_fn, x[trim], y[trim])
        angle, scale = abs(popt[0]), abs(popt[1]) * 2
        dists  = np.array([anisotropy_fn(x[trim][j], *popt)-y[trim][j] for j in range(len(trim[0]))])
        # mean_dist = (1.1 - np.mean(np.abs(dists)) / scale) ** 2
        if scale < amp_cutoff or scale > 5 or angle < 1 or angle > 2.5:
            return 0
        index = round((scale * angle) ** 2 / 8, 2)
        if details:
            return x, y, shift, popt, index, scale, angle
        return index
    except:
        return None

def calc_index_windowed(time, variations, directions, window: int = 3):
    sorted = np.argsort(directions)
    variations, directions = variations[:,sorted], directions[sorted]
    result = []
    for i in range(window, len(time)):
        x = np.concatenate([directions + time[i-t] * 360 / 86400 for t in range(window)]) % 360
        y = np.concatenate([variations[i-t] for t in range(window)])
        filter = np.isfinite(y)
        x, y = x[filter], y[filter]
        result.append(precursor_idx(x, y))
    return time[window:].tolist(), result

def index_details(time, variations, directions, when, window: int = 3):
    idx = np.where(time == when)[0]
    if not idx: return {}
    sorted = np.argsort(directions)
    variations, directions = variations[:,sorted], directions[sorted]
    x = np.concatenate([directions + time[idx[0]-t] * 360 / 86400 for t in range(window)]) % 360
    y = np.concatenate([variations[idx[0]-t] for t in range(window)])
    filter = np.isfinite(y)
    x, y = x[filter], y[filter]
    res = precursor_idx(x, y, details=True)
    if not res: return {}
    x, y, shift, popt, index, scale, angle = res
    x = (x - shift + 360) % 360
    sorted = np.argsort(x)
    x, y = x[sorted], y[sorted]
    return dict({
        'time': int(time[idx[0]]),
        'x': x.tolist(),
        'y': y.tolist(),
        'fn': np.round(anisotropy_fn(x, *popt), 3).tolist(),
        'index': index,
        'amplitude': scale,
        'angle': angle
    })

def get(t_from, t_to, exclude=[], details=None):
    t_from = t_from // database.PERIOD * database.PERIOD
    stations = [k for k in RING.keys() if k not in exclude]
    data, filtered, excluded = _filter(database.fetch((t_from, t_to), stations))
    base_idx = _determine_base(data)
    base_data = data[base_idx[0]:base_idx[1], 1:]
    time = np.uint64(data[:,0])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        warnings.simplefilter('ignore', optimize.OptimizeWarning)
        variation = data[:,1:] / np.nanmean(base_data, axis=0) * 100 - 100
        directions = [_get_direction(s) for s in stations]
        print(variation.shape)
        if details:
            return index_details(time, variation, np.array(directions), int(details))
        prec_idx = calc_index_windowed(time, variation, np.array(directions))
    return dict({
        'base': int(data[base_idx[0], 0]),
        'time': time.tolist(),
        'variation': np.where(np.isnan(variation), None, np.round(variation, 2)).tolist(),
        'shift': directions,
        'station': list(stations),
        'precursor_idx': prec_idx,
        'filtered': filtered,
        'excluded': exclude + [stations[i] for i in excluded]
    })

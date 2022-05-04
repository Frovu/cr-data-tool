from data_source.neutron import database
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

# TODO: calculate asymptotic direction
def _get_direction(station):
    return RING[station]

def get(t_from, t_to):
    t_from = t_from // database.PERIOD * database.PERIOD
    stations = RING.keys()
    data = database.fetch((t_from, t_to), stations)
    base_idx = _determine_base(data)
    base_data = data[base_idx[0]:base_idx[1], 1:]
    base_data = base_data
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        variation = data[:,1:] / np.nanmean(base_data, axis=0) - 1
    variation = np.round(variation * 100, 2)
    return dict({
        'base': int(data[base_idx[0], 0]),
        'time': np.uint64(data[:,0]).tolist(),
        'variation': np.where(np.isnan(variation), None, variation).tolist(),
        'shift': [_get_direction(s) for s in stations],
        'station': list(stations)
    })

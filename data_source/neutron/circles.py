from data_source.neutron import database
import numpy as np

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
    slice = 0, -1
    period = data[slice[0]][0], data[slice[1]][0]
    return period, slice

# TODO: calculate asymptotic direction
def _get_direction(station):
    return RING[station]

def get(t_from, t_to):
    t_from = t_from // database.PERIOD * database.PERIOD
    stations = RING.keys()
    data = database.fetch((t_from, t_to), stations)
    base_period, base_idx = _determine_base(data)
    base_data = data[base_idx[0]:base_idx[1], 1:]
    variation = data[:,1:] / np.mean(base_data, axis=0) - 1
    variation = np.round(variation * 100, 2)
    return dict({
        'time': np.uint64(data[:,0]).tolist(),
        'variation': np.where(np.isnan(variation), None, variation).tolist(),
        'shift': [_get_direction(s) for s in stations],
        'station': list(stations)
    })

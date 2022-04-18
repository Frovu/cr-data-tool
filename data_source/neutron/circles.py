from data_source.neutron import database
import numpy as np

# name: [ longitude, R cutoff ]
RING = dict({
    'OULU': [ 25.47, 0.9 ],
    'APTY': [ 33.39, 0.5 ],
    'KERG': [ 70.25, 1.14 ],
    'NRLK': [ 88.05, 0.63 ],
    # 'IRKT': [ 104.03, 3.64 ],
    # 'YKTK': [ 129.43, 1.65 ],
    # 'INVK': [ -133.72, 0.3 ],
})

def _determine_base(data):
    slice = 0, -1
    period = data[slice[0]][0], data[slice[1]][0]
    return period, slice

def _get_direction(station):
    # TODO: asymptotic direction
    lon = RING[station][0]
    return lon

def get(t_from, t_to):
    stations = RING.keys()
    data = database.fetch((t_from, t_to), stations)
    base_period, base_idx = _determine_base(data)
    base_data = data[base_idx[0]:base_idx[1], 1:]
    variation = data[:,1:] / np.mean(base_data, axis=0) - 1
    shift = [_get_direction(s) for s in stations]
    return dict({
        'time': np.uint64(data[:,0]).tolist(),
        'variation': np.round(variation * 100, 2).tolist(),
        'shift': shift
    })

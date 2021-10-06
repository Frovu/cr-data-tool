import data_source.muones.db_proxy as proxy
import numpy as np

BATCH_SIZE = 4096
COLUMNS_TEMP = ['T_m']
COLUMNS_RAW = ['raw_acc_cnt', 'n_v_raw', 'pressure']

def _calculate_temperatures(lat, lon, t_from, t_to, period):
    pass

def _prepare(what, station, t_from, t_to, period):
    lat, lon = proxy.coordinates(station)
    target_columns = COLUMNS_TEMP if what == 'temperature' else COLUMNS_RAW
    missing = proxy.analyze_integrity(station, t_from, t_to, period, target_columns[0])
    for interval in missing:
        batch = period*BATCH_SIZE
        for i_start in range(interval[0], interval[1], batch):
            i_end = i_start+batch if i_start+batch < interval[1] else interval[1]
            if what == 'temperature':
                data = _calculate_temperatures(lat, lon, i_start, i_end, period)
            elif what == 'raw':
                data = parser.obtain(station, i_start, i_end, period)
            parser.upsert(station, period, data, target_columns)

def correct(station, t_from, t_to, period):
    _prepare('temperature', station, t_from, t_to, period)
    _prepare('raw', station, t_from, t_to, period)
    raw = parser.obtain(station, t_from, t_to, period)
    temperatures = _calculate_temperatures(lat, lon, t_from, t_to, period)
    proxy.upsert(station, period, result)
    pass

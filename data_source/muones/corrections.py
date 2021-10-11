import data_source.muones.db_proxy as proxy
import data_source.muones.obtain_data as parser
import numpy as np

BATCH_SIZE = 4096
COLUMNS_TEMP = ['T_m']
COLUMNS_RAW = ['raw_acc_cnt', 'n_v_raw', 'pressure']

def _calculate_temperatures(lat, lon, t_from, t_to, period):
    return []

def _prepare(station, t_from, t_to, period, integrity_column, process_fn):
    missing = proxy.analyze_integrity(station, t_from, t_to, period, integrity_column)
    for interval in missing:
        batch = period*BATCH_SIZE
        for i_start in range(interval[0], interval[1], batch):
            i_end = i_start+batch if i_start+batch < interval[1] else interval[1]
            process_fn(i_start, i_end)

def correct(station, t_from, t_to, period):
    lat, lon = proxy.coordinates(station)
    _prepare(station, t_from, t_to, period, COLUMNS_TEMP[0],
        lambda a, b: proxy.upsert(station, period, _calculate_temperatures(lat, lon, a, b, period), COLUMNS_TEMP))
    _prepare(station, t_from, t_to, period, COLUMNS_RAW[0],
        lambda a, b: proxy.upsert(station, period, parser.obtain(station, period, a, b), COLUMNS_RAW))

from datetime import datetime, timezone
t_strt = datetime(2021, 10, 4).replace(tzinfo=timezone.utc).timestamp()
t_end = datetime(2021, 10, 7, 12).replace(tzinfo=timezone.utc).timestamp()
correct('Moscow', t_strt, t_end, 3600)
# for r in correct('Moscow', dt_strt, dt_end, 60):
#     print(*r)

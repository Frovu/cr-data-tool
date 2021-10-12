from core.sequence_filler import SequenceFiller, fill_fn
import data_source.muones.db_proxy as proxy
import data_source.muones.corrections as corrections
from math import floor, ceil

scheduler = SequenceFiller()

def _data_worker(station, t_from, t_to, period):
    pass

def station(lat, lon):
    return proxy.station(lat, lon)

# # TODO: include query arg to select only some values
# def get_everything(station, t_from, t_to, period=60):

def get_correlation(station, t_from, t_to, period=3600):
    token = 'mcorr'+station+str(period)
    t_from = floor(t_from / period) * period
    t_to = ceil(t_to / period) * period
    is_done, info = scheduler.status((token, t_from, t_to))
    if is_done == False:
        return 'busy', info
    if is_done or not proxy.analyze_integrity(station, t_from, t_to, period, ['T_m', 'raw_acc_cnt']):
        return 'ok', proxy.select(station, t_from, t_to, period, ['T_m', 'n_v_raw'])
    scheduler.do_fill(token, t_from, t_to, period, corrections.get_prepare_tasks(station, period, fill_fn))
    return 'accepted', None

from datetime import datetime, timezone
import time
t_strt = datetime(2021, 8, 1).replace(tzinfo=timezone.utc).timestamp()
t_end = datetime(2021, 10, 1).replace(tzinfo=timezone.utc).timestamp()
while True:
    status, data = get_correlation('Moscow', t_strt, t_end, 60)
    if status == 'ok':
        print('done', len(data))
        break
    print(status, data)
    time.sleep(1)

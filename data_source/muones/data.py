from core.sequence_filler import Scheduler
import data_source.muones.db_proxy as proxy
import data_source.muones.corrections as corrections
from math import floor, ceil

scheduler = Scheduler()

def _data_worker(station, t_from, t_to, period):
    pass

def station(lat, lon):
    return proxy.station(lat, lon)

# # TODO: include query arg to select only some values
# def get_everything(station, t_from, t_to, period=60):

def get_correlation(station, t_from, t_to, columns=['T_m', 'n_v_raw'], period=3600):
    token = 'mcorr'+"".join(columns)+station+str(period)
    t_from = floor(t_from / period) * period
    t_to = ceil(t_to / period) * period
    is_done, info = scheduler.get(token, t_from, t_to)
    if is_done == False:
        return 'busy', info
    if is_done or not proxy.analyze_integrity(station, t_from, t_to, period, columns):
        return 'ok', proxy.select(station, t_from, t_to, period, columns)
    scheduler.schedule(token, t_from, t_to, period, [
        'mass-avg temp', lambda 
    ])
    return 'accepted', None

from datetime import datetime, timezone
import time
t_strt = datetime(2021, 3, 4).replace(tzinfo=timezone.utc).timestamp()
t_end = datetime(2021, 10, 4, 12).replace(tzinfo=timezone.utc).timestamp()
while True:
    status, data = get_correlation('Moscow', t_strt, t_end)
    if status == 'ok':
        print('done', len(data))
        break
    print(status)
    time.sleep(1)

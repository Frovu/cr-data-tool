from core.sequence_filler import SequenceFiller, fill_fn
import data_source.muones.db_proxy as proxy
import data_source.muones.obtain_data as parser
import data_source.muones.corrections as corrections
from math import floor, ceil

scheduler = SequenceFiller()

def _data_worker(station, t_from, t_to, period):
    pass

def stations():
    return proxy.stations()

def station(lat, lon):
    return proxy.station(lat, lon)

# # TODO: include query arg to select only some values
# def get_everything(station, t_from, t_to, period=60):

def get_correlation(station, t_from, t_to, period=3600, against='pressure'):
    if against == 'Tm': against = 'T_m'
    if not proxy.coordinates(station) or against not in ['T_m', 'pressure']:
        return 'unknown', None
    token = 'corr'+against+station+str(period)
    t_from = floor(t_from / period) * period
    t_to = ceil(t_to / period) * period
    is_done, info = scheduler.status((token, t_from, t_to))
    if is_done == False:
        return 'failed' if info.get('failed') else 'busy', info
    int_columns = 'raw_acc_cnt' if against=='pressure' else [against, 'raw_acc_cnt']
    if is_done or not proxy.analyze_integrity(station, t_from, t_to, period, int_columns):
        return 'ok', proxy.select(station, t_from, t_to, period, [against, 'n_v_raw'], include_time=False, order=against)
    mq_fn = lambda q: scheduler.merge_query(token, t_from, t_to, q)
    scheduler.do_fill(token, t_from, t_to, period, corrections.get_prepare_tasks(station, period, fill_fn, mq_fn, against))
    return 'accepted', None

def get_raw(station, t_from, t_to, period=3600):
    if station not in ['Moscow']:
        return 'unknown', None
    t_from, t_to = period * floor(t_from / period), period * ceil(t_to / period)
    return 'ok', parser.obtain_raw(station, t_from, t_to, period)

from core.sequence_filler import SequenceFiller, fill_fn
import data_source.muones.db_proxy as proxy
import data_source.muones.obtain_data as parser
import data_source.muones.corrections as corrections
from math import floor, ceil

scheduler = SequenceFiller()

def stations():
    return proxy.stations()

def station(lat, lon):
    return proxy.station(lat, lon)

def get_corrected(station, t_from, t_to, period=3600, channel='V', recalc=True):
    if not proxy.coordinates(station):
        return 'unknown', None
    token = station + str(period)
    t_from = floor(t_from / period) * period
    t_to = ceil(t_to / period) * period
    args = (station, t_from, t_to, period, channel)
    is_done, info = scheduler.status((token, t_from, t_to))
    if is_done == False:
        return 'failed' if info.get('failed') else 'busy', info
    if is_done or not proxy.analyze_integrity(*args, ['raw_acc_cnt', 'T_m']):
        if recalc or proxy.analyze_integrity(*args):
            return 'ok', corrections.correct(*args)
        return 'ok', proxy.select(*args, ['count_raw', 'n_v', 'pressure', 'T_m'])
    mq_fn = lambda q: scheduler.merge_query(token, t_from, t_to, q)
    scheduler.do_fill(token, t_from, t_to, period,
        corrections.get_prepare_tasks(station, period, channel, fill_fn, mq_fn))
    return 'accepted', None

def get_correlation(station, t_from, t_to, period=3600, channel='V', against='pressure', what='count_raw'):
    if against == 'Tm': against = 'T_m'
    if not proxy.coordinates(station) or against not in ['T_m', 'pressure']:
        return 'unknown', None
    # FIXME: this leads to duplicate raw data calculations (but nobody cares)
    token = 'corr'+against+station+str(period)
    t_from = floor(t_from / period) * period
    t_to = ceil(t_to / period) * period
    args = (station, t_from, t_to, period, channel)
    is_done, info = scheduler.status((token, t_from, t_to))
    if is_done == False:
        return 'failed' if info.get('failed') else 'busy', info
    int_columns = 'raw_acc_cnt' if against=='pressure' else [against, 'raw_acc_cnt']
    if is_done or not proxy.analyze_integrity(*args, int_columns):
        data = proxy.select(*args, [against, what], include_time=False, order=against)
        return 'ok', corrections.calc_correlation(*data)
    mq_fn = lambda q: scheduler.merge_query(token, t_from, t_to, q)
    scheduler.do_fill(token, t_from, t_to, period,
        corrections.get_prepare_tasks(station, period, channel, fill_fn, mq_fn))
    return 'accepted', None

def get_raw(station, t_from, t_to, period=3600):
    if station not in ['Moscow']:
        return 'unknown', None
    t_from, t_to = period * floor(t_from / period), period * ceil(t_to / period)
    return 'ok', parser.obtain_raw(station, t_from, t_to, period)

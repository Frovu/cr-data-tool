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

def _get_prepare(station, t_from, t_to, period, channel, corrected=True):
    if not ch := proxy.channel(station, channel, period):
        return 'unknown', None
    token = station + channel + str(period)
    interv = (floor(t_from / period) * period, ceil(t_to / period) * period)
    is_done, info = scheduler.status((token, *interv))
    if is_done == False:
        return 'failed' if info.get('failed') else 'busy', info
    if is_done or not proxy.analyze_integrity(channel, interv, corrected):
        return 'ok', (ch, interv)
    mq_fn = lambda q: scheduler.merge_query(token, *interv, q)
    scheduler.do_fill(token, *interv, period,
        corrections.get_prepare_tasks(station, period, channel, fill_fn, mq_fn))
    return 'accepted', None

def get_corrected(station, t_from, t_to, period=3600, channel='V', recalc=True):
    status, info = _get_prepare(station, t_from, t_to, period, channel)
    if status == 'ok':
        # TODO: get corrected integrity and correct
        return 'ok', proxy.select(*info, ['count_raw', 'n_v', 'pressure', 'T_m'])
    return status, info

def get_correlation(station, t_from, t_to, period=3600, channel='V', against='pressure', what='count_raw'):
    if against == 'Tm': against = 'T_m'
    if against not in ['T_m', 'pressure']:
        return 'unknown', None
    status, info = _get_prepare(station, t_from, t_to, period, channel, corrected=False)
    if status == 'ok':
        data = proxy.select(*info, [against, what], include_time=False, where=what+' > 0', order=against)
        return 'ok', corrections.calc_correlation(*data)
    return status, info

def get_raw(station, t_from, t_to, period=3600):
    if station not in ['Moscow']:
        return 'unknown', None
    t_from, t_to = period * floor(t_from / period), period * ceil(t_to / period)
    return 'ok', parser.obtain_raw(station, t_from, t_to, period)

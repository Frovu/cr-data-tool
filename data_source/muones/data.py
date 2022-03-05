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

def _get_prepare(station, t_from, t_to, period, channel, columns=['corrected']):
    token = station + channel + str(period)
    interv = (floor(t_from / period) * period, ceil(t_to / period) * period)
    is_done, info = scheduler.status((token, *interv))
    if is_done == False:
        return 'failed' if info.get('failed') else 'busy', info
    ch = proxy.channel(station, channel, period)
    if not ch:
        return 'unknown', None
    if is_done or not proxy.analyze_integrity(ch, interv, columns):
        return 'ok', (ch, interv)
    mq_fn = lambda q: scheduler.merge_query(token, *interv, q)
    scheduler.do_fill(token, *interv, period,
        corrections.get_prepare_tasks(ch, fill_fn, mq_fn))
    return 'accepted', None

def get_corrected(station, t_from, t_to, period=3600, channel='V'):
    status, info = _get_prepare(station, t_from, t_to, period, channel, ['source', 'T_m', 'pressure'])
    if status == 'ok':
        res = corrections.corrected(*info)
        if not res:
            return 'failed', {'failed': 'No data'}
        return 'ok', res
    return status, info

def get_correlation(station, t_from, t_to, period=3600, channel='V', against='pressure', what='source'):
    if against == 'Tm': against = 'T_m'
    if against not in ['T_m', 'pressure']:
        return 'unknown', None
    status, info = _get_prepare(station, t_from, t_to, period, channel, [against, what])
    if status == 'ok':
        data = proxy.select(*info, [against, what], include_time=False, where=what+' > 0', order=against)
        if len(data[0]) < 72:
            return 'failed', {'failed': 'No data'}
        return 'ok', corrections.calc_correlation(*data)
    return status, info

def get_raw(station, t_from, t_to, period=3600):
    if station not in ['Moscow']:
        return 'unknown', None
    t_from, t_to = period * floor(t_from / period), period * ceil(t_to / period)
    return 'ok', parser.obtain_raw(station, t_from, t_to, period)

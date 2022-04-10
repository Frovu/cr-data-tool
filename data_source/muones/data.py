from core.sequence_filler import SequenceFiller, fill_fn
import data_source.muones.db_proxy as proxy
import data_source.muones.obtain_data as parser
import data_source.muones.corrections as corrections
from datetime import datetime
from math import floor, ceil

scheduler = SequenceFiller(ttl=0)

def stations():
    return proxy.stations()

def station(lat, lon):
    return proxy.station(lat, lon)

def _get_prepare(station, t_from, t_to, period, channel, columns=['corrected']):
    token = station + channel + str(period)
    key = (token, t_from, t_to)
    is_done, info = scheduler.status(key)
    if is_done == False:
        return 'failed' if info.get('failed') else 'busy', info
    ch = proxy.channel(station, channel, period)
    trim_past, trim_future = ch.since, datetime.now().timestamp()
    t_from = t_from if t_from > trim_past else trim_past
    t_to = t_to if t_to < trim_future else trim_future
    interv = (floor(t_from / period) * period, ceil(t_to / period) * period)
    if not ch:
        return 'unknown', None
    if is_done or not proxy.analyze_integrity(ch, interv, columns):
        return 'ok', (ch, interv)
    mq_fn = lambda q: scheduler.merge_query(*key, q)
    scheduler.do_fill(token, *interv, period,
        corrections.get_prepare_tasks(ch, fill_fn, mq_fn), key_overwrite=key)
    return 'accepted', None

def get_corrected(station, t_from, t_to, period=3600, channel='V', coefs='saved'):
    status, info = _get_prepare(station, t_from, t_to, period, channel, ['source', 'T_m', 'pressure'])
    if status == 'ok':
        res = corrections.corrected(*info, coefs)
        if not res:
            return 'failed', {'failed': 'No data'}
        return 'ok', res
    return status, info

def get_correlation(station, t_from, t_to, period=3600, channel='V', against='pressure', what='source', only=None):
    if against == 'Tm': against = 'T_m'
    if against not in ['T_m', 'pressure', 'all']:
        return 'unknown', None
    status, info = _get_prepare(station, t_from, t_to, period, channel, ['source', 'T_m', 'pressure'])
    if status == 'ok':
        if against == 'all':
            return 'ok', corrections.calc_coefs(*info)
        data = proxy.select(*info, [against, what], include_time=False,
            where=f'{what} > 0 AND {against} > 0', order=against)
        if len(data[0]) < 72:
            return 'failed', {'failed': 'No data'}
        return 'ok', corrections.calc_correlation(*data, only)
    return status, info

def get_raw(station, t_from, t_to, period=3600):
    if station not in ['Moscow-pioneer']:
        return 'unknown', None
    trim_future = datetime.now().timestamp()
    t_to = t_to if t_to < trim_future else trim_future
    t_from, t_to = period * floor(t_from / period), period * ceil(t_to / period)
    return 'ok', parser.obtain_raw(station, t_from, t_to, period)

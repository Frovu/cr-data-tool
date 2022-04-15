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

def _get_prepare_tasks(channel, fill_fn, subquery_fn, temp_mode):
    temp_fn = corrections.t_mass_average if temp_mode == 'T_m' else corrections.t_effective
    return [
        ('raw counts', fill_fn, (
            lambda i: proxy.analyze_integrity(channel, i, 'source'),
            lambda i: proxy.upsert(channel, *parser.obtain(channel, *i, 'source')),
            False, 1, 365*24
        )),
        ('pressure', fill_fn, (
            lambda i: proxy.analyze_integrity(channel, i, 'pressure'),
            lambda i: proxy.upsert(channel, *parser.obtain(channel, *i, 'pressure')),
            False, 1, 365*24
        )),
        ('temperature-model', fill_fn, (
            lambda i: proxy.analyze_integrity(channel, i, temp_mode),
            lambda i: proxy.upsert(channel, temp_fn(channel, *i, subquery_fn), temp_mode, epoch=True),
            True, 8, 365*24
        ))
    ]

def _get_prepare(station, t_from, t_to, period, channel, columns):
    token = station + channel + str(period)
    key = (token, t_from, t_to)
    is_done, info = scheduler.status(key)
    if is_done == False:
        return 'failed' if info.get('failed') else 'busy', info
    ch = proxy.channel(station, channel, period)
    if not ch:
        return 'unknown', None
    trim_past, trim_future = ch.since, datetime.now().timestamp()
    t_from = t_from if t_from > trim_past else trim_past
    t_to = t_to if t_to < trim_future else trim_future
    interv = (floor(t_from / period) * period, ceil(t_to / period) * period)
    if is_done or not proxy.analyze_integrity(ch, interv, columns):
        return 'ok', (ch, interv)
    mq_fn = lambda q: scheduler.merge_query(*key, q)
    temp_mode = 'T_m' if 'T_m' in columns else 'T_eff'
    scheduler.do_fill(token, *interv, period,
        _get_prepare_tasks(ch, fill_fn, mq_fn, temp_mode), key_overwrite=key)
    return 'accepted', None

def get_corrected(station, t_from, t_to, period=3600, channel='V', coefs='saved', temp='T_m'):
    if temp == 'T_eff' and station not in ['Nagoya']:
        return 'failed', {'failed': 'T_eff not supported'}
    status, info = _get_prepare(station, t_from, t_to, period, channel, ['source', temp, 'pressure'])
    if status == 'ok':
        res = corrections.corrected(*info, coefs, temp)
        if not res:
            return 'failed', {'failed': 'No data'}
        return 'ok', res
    return status, info

def get_correlation(station, t_from, t_to, period=3600, channel='V', against='pressure', what='source', only=None):
    if against == 'Tm': against = 'T_m'
    if against == 'Teff': against = 'T_eff'
    if against not in ['T_m', 'T_eff', 'pressure', 'all']:
        return 'unknown', None
    if against == 'T_eff' and station not in ['Nagoya']:
        return 'failed', {'failed': 'T_eff not supported'}
    columns = ['source', against] if against != all else ['source', 'T_m', 'pressure']
    status, info = _get_prepare(station, t_from, t_to, period, channel, columns)
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

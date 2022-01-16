import data_source.temperature_model.temperature as temperature
import data_source.stations_meteo.db_proxy as proxy
import data_source.stations_meteo.parser as parser
from core.sequence_filler import SequenceFiller, fill_fn
from datetime import datetime, timezone
from math import floor, ceil
import logging as log

scheduler = SequenceFiller(ttl=15)
completed_query_chache = dict()
PERIOD = 3600

def get_with_model(lat, lon, t_from, t_to, period=PERIOD):
    lat = round(float(lat), 2)
    lon = round(float(lon), 2)
    token = (lat, lon)
    t_from, t_to = period * floor(t_from / period), period * ceil(t_to / period)
    key = (token, t_from, t_to)
    t_trim = datetime.utcnow().replace(tzinfo=timezone.utc).timestamp() // period * period - period
    if t_trim > t_to: t_trim = t_to
    is_done, info = scheduler.status(key)
    if is_done == False:
        return 'failed' if info.get('failed') else 'busy', info
    station = proxy.select_station(lat, lon)
    if not parser.supported(station):
        return temperature.get(lat, lon, t_from, t_to)
    model_status, model_r = temperature.get(lat, lon, t_from, t_to, True)
    if model_status ==  'unknown':
        return model_status, model_r
    if model_status == 'ok' and not proxy.analyze_integrity(station, t_from, t_trim):
        return 'ok', proxy.select(station, t_from, t_to, True)
    log.info(f'LOCAL METEO: Satisfying {station} {t_from}:{t_trim}')
    q = scheduler.do_fill(token, t_from, t_trim, period,
        parser.get_tasks(station, period, fill_fn), key_overwrite=key)
    if model_status == 'accepted':
        model_r.append_tasks(q.tasks) # use temp_model query object
        scheduler.query(key, model_r)
    return 'accepted', None

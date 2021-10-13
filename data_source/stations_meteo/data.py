import data_source.temperature_model.temperature as temperature
import data_source.stations_meteo.db_proxy as proxy
import data_source.stations_meteo.parser as parser
from core.sequence_filler import SequenceFiller, fill_fn
from datetime import datetime
from math import floor, ceil

scheduler = SequenceFiller(ttl=15)
completed_query_chache = dict()
PERIOD = 3600

def get_with_model(lat, lon, t_from, t_to, period=PERIOD):
    lat = round(float(lat), 2)
    lon = round(float(lon), 2)
    token = (lat, lon)
    t_from, t_to = period * floor(t_from / period), period * ceil(t_to / period)
    is_done, info = scheduler.status((token, t_from, t_to))
    if is_done == False:
        return 'failed' if info.get('failed') else 'busy', info
    dt_from = datetime.utcfromtimestamp(t_from)
    dt_to = datetime.utcfromtimestamp(t_to)
    station = proxy.select_station(lat, lon)
    if not parser.supported(station):
        return temperature.get(lat, lon, dt_from, dt_to)
    model_status, model_r = temperature.get(lat, lon, dt_from, dt_to, True)
    if model_status ==  'unknown':
        return model_status, model_r
    if model_status == 'ok' and not proxy.analyze_integrity(station, t_from, t_to):
        return 'ok', proxy.select(station, t_from, t_to, True)
    scheduler.do_fill(token, t_from, t_to, period, parser.get_tasks(station, period, fill_fn))
    if model_status == 'accepted':
        scheduler.merge_query(token, t_from, t_to, model_r)
    return 'accepted', None

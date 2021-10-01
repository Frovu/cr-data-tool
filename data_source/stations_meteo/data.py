import data_source.temperature_model.temperature as temperature
import data_source.stations_meteo.db_proxy as proxy
import data_source.stations_meteo.parser as parser
from threading import Thread
from datetime import datetime, timedelta

_lock = False
completed_query_chache = dict()

# TODO: implement Thread spawn mechanism if needed
# def get(station, dt_from, dt_to):
#     pass
# def get_with_coords(lat, lon, dt_from, dt_to):
#     station = proxy.select_station(lat, lon)
#     return None if station is None else get(station, dt_from, dt_to)

def is_hopeless(station, dt_from, dt_to):
    return completed_query_chache.get((station, dt_from, dt_to))

def fill_worker(station, dt_from, dt_to):
    ok = parser.fill_interval(station, [dt_from, dt_to], ['t2', 'pressure'])
    if ok and dt_to < datetime.now() - timedelta(hours=1):
        completed_query_chache[(station, dt_from, dt_to)] = True
    global _lock
    _lock = False

def get_with_model(lat, lon, dt_from, dt_to):
    station = proxy.select_station(lat, lon)
    if station is None or not parser.supported(station):
        return 'unknown', None
    local_ready = proxy.analyze_integrity(station, dt_from, dt_to)
    model_status, model_p = temperature.get(lat, lon, dt_from, dt_to, True)
    if local_ready or is_hopeless(station, dt_from, dt_to):
        if model_status != 'ok':
            return model_status, model_p
        return 'ok', proxy.select(station, dt_from, dt_to, True)
    else:
        global _lock
        if _lock: return 'busy', parser.get_progress()
        thread = Thread(target=fill_worker, args=(station, dt_from, dt_to))
        _lock = True
        thread.start()
        if model_status == 'ok':
            return 'accepted', None
        else:
            return model_status, model_p

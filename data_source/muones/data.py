import data_source.muones.db_proxy as proxy
from threading import Thread

_lock = False

def _data_worker(station, dt_from, dt_to):
    pass

def station(lat, lon):
    return proxy.station(lat, lon)

# TODO: include query arg to select only some values
def get(station, dt_from, dt_to):
    ready = proxy.analyze_integrity(station, dt_from, dt_to)
    if ready:
        return 'ok', proxy.select(station, dt_from, dt_to)
    if _lock:
        return 'busy', None
    thread = Thread(target=_data_worker, args=(station, dt_from, dt_to))
    _lock = True
    thread.start()

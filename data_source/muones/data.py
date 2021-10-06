import data_source.muones.db_proxy as proxy
from threading import Thread

_lock = False

def _data_worker(station, t_from, t_to):
    pass

def station(lat, lon):
    return proxy.station(lat, lon)

# TODO: include query arg to select only some values
def get_everything(station, t_from, t_to, period=60):
    global _lock
    if _lock:
        return 'busy', None
    missing = proxy.analyze_integrity(station, t_from, t_to, period)
    if not missing:
        return 'ok', proxy.select(station, t_from, t_to, period)
    thread = Thread(target=_data_worker, args=(station, t_from, t_to))
    _lock = True
    thread.start()

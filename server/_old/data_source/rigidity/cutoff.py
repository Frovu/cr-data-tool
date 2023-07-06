import data_source.rigidity.database as database
import data_source.rigidity.particle as particle
from core.scheduler import Scheduler
import logging

scheduler = Scheduler(ttl=0)

DEFAULT_ALTITUDE = 20 # km above sea level

def _hash(params):
    return hash(params[2:])

def _calculate(time, model, lat, lon, vertical, azimuthal, alt):
    logging.info(f'Cutoff: calculating {time} ({lat},{lon},{vertical},{azimuthal},{alt})')
    pass

def validate_params(time, model, lat, lon, vertical, azimuthal, alt):
    return True # TODO

@scheduler.wrap(argc=6)
def cutoff(time, lat, lon, vertical, azimuthal, alt=DEFAULT_ALTITUDE, model='', exact=False):
    params = (time, model, lat, lon, vertical, azimuthal, alt)
    if result := database.select(time, _hash(params), model, *(None,) if exact else ()):
        return result, None, None
    if error := validate_params(*params):
        return None, error, None
    return None, None, [(_calculate, params, 'cutoff rigidity', True)]

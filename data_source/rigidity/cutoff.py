import data_source.rigidity.database as database
import data_source.rigidity.particle as particle
from core.scheduler import Scheduler
import logging

scheduler = Scheduler(ttl=0)

DEFAULT_ALTITUDE = 20 # km above sea level

def _calculate(time, lat, lon, vertical, azimuthal, alt, model):
    pass

def validate_params(time, lat, lon, vertical, azimuthal, altitude):
    return True # TODO

@scheduler.wrap(argc=6)
def cutoff(time, lat, lon, vertical, azimuthal, alt=DEFAULT_ALTITUDE, model='', exact=False):
    if result := database.select(params, model, *(None,) if exact else ()):
        return result, None
    logging.info(f'Cutoff: calculating {time} ({lat},{lon},{vertical},{azimuthal},{alt})')
    tasks = [(_calculate, (time, lat, lon, vertical, azimuthal, alt, model), 'cutoff rigidity', True)]
    return None, tasks

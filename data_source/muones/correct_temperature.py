import data_source.muones.db_proxy as proxy
import numpy as np

def _calculate_temperatures(lat, lon, dt_from, dt_to):
    pass

# TODO: calculate only where required
def _prepare_temperatures(lat, lon, dt_from, dt_to):
    _calculate_temperatures(lat, lon, dt_from, dt_to)

def get_corrected(station, dt_from, dt_to):
    proxy.fill_raw(station, dt_from, dt_to)
    lat, lon = proxy.coordinates(station)
    temperatures = _prepare_temperatures(lat, lon, dt_from, dt_to)
    proxy.update(station, temperatures, 'T_m')
    pass

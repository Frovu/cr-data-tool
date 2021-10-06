import data_source.muones.db_proxy as proxy
import numpy as np

BATCH_SIZE = 4096

def _calculate_temperatures(lat, lon, dt_from, dt_to, interval):
    pass

def correct(station, dt_from, dt_to, period):
    lat, lon = proxy.coordinates(station)
    raw = parser.obtain(station, dt_from, dt_to, period)
    temperatures = _calculate_temperatures(lat, lon, dt_from, dt_to, interval)
    proxy.upsert(station, period, result)
    pass

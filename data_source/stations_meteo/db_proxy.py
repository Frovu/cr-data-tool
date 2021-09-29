
from data_source.temperature_model.proxy import pg_conn

def _table_name(station_name):
    return f'local_meteo_{station_name}'

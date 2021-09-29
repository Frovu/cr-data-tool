import data_source.stations_meteo.parser as parser

def query(station, time_range, query):
    return parser.query(station, time_range, query)

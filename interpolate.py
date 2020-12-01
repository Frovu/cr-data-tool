import numpy as np
from netCDF4 import Dataset, num2date, date2index
from datetime import datetime

def _interpolate(line, tick_min=60):
    return line

def _extract(filename, lat, lon, start_time, end_time):
    data = Dataset(filename, 'r')
    print(data.title)
    assert "NMC reanalysis" in data.title
    air = data.variables["air"]
    times = data.variables["time"]
    lat_idx = np.where(data.variables["lat"][:] == lat)
    lon_idx = np.where(data.variables["lon"][:] == lon)
    start_idx = date2index(start_time, times)
    end_idx = date2index(end_time, times)
    print(f"lat={lat} lon={lon} from={start_time.date()}({start_idx}) to={end_time.date()}({end_idx})")
    for level_i, level in enumerate(data.variables["level"][:]):
        line = [a[level_i][lat][lon] for a in air[start_idx:end_idx]]
        print(f'{level}:\t{"  ".join([str("%.1f" % i) for i in line])}')

_extract('./tmp/air.nc/air.2020.nc', 0, 0,
    datetime.strptime('2020-01-01', '%Y-%m-%d'),
    datetime.strptime('2020-01-02', '%Y-%m-%d'))

import requests
import logging
import pygrib
from datetime import datetime
import numpy as np
from scipy import interpolate, ndimage
from data_source.temperature_model.proxy import LEVELS
from concurrent.futures import ThreadPoolExecutor

_GFS_URL = 'https://nomads.ncep.noaa.gov'
_GFS_URL += '/cgi-bin/filter_gfs_0p25_1hr.pl'
_GFS_QUERY_VARS = '&var_TMP=on' + ''.join([f'&lev_{str(lvl)}_mb=on' for lvl in LEVELS])

def _download(latlon, fcst_date, fcst_hour, filename):
    hh, yyyymmdd = f'{fcst_date.hour:02}', fcst_date.strftime("%Y%m%d")
    query = f'?file=gfs.t{hh}z.pgrb2.0p25.f{fcst_hour:03}'
    query += f'&dir=%2Fgfs.{yyyymmdd}%2F{hh}%2Fatmos'
    query += f'&subregion=&leftlon={latlon[0][0]}&rightlon={latlon[0][1]}&bottomlat={latlon[1][0]}&toplat={latlon[1][1]}'
    try:
        res = requests.get(f'{_GFS_URL}{query}{_GFS_QUERY_VARS}', stream=True)
        if res.status_code != 200:
            raise Exception('GFS failed')
        with open(filename, 'wb') as f:
            for chunk in res.iter_content(1024):
                f.write(chunk)
        return filename
    except:
        logging.error(f'Failed to get GFS data of {yyyymmdd}/{hh}+{fcst_hour:03}')
        return False

def _calc_one_hour(timestamp, latlon):
    dtime = datetime.utcfromtimestamp(timestamp)
    fname = dtime.strftime("tmp/gfs.%Y%m%d.%H.grb2")
    if _download(latlon, dtime, 6, fname):
        grbs = pygrib.open(fname)
        latlons = grbs.message(1).latlons()
        data = np.empty((len(LEVELS), *latlons[0].shape))
        grbs.rewind()
        for grb in grbs:
            print(grb)
            if grb.level < 10:
                print(grb.level, grb.values)
                continue
            data[LEVELS.index(grb.level)] = grb.values
            print(grb.level, LEVELS.index(grb.level))
        print(data)
        # ndimage.map_coordinates(data[i][j], coords, mode='wrap')

# grid_margin determines size of queried subregion of coordinates (required for spline interp)
def obtain(lat, lon, t_from, t_to, grid_margin=1, PERIOD=3600):
    latlon = ( (lat - grid_margin, lat + grid_margin),
               (lon - grid_margin, lon + grid_margin) )
    times = [t for t in range(t_from, t_to + 1, PERIOD)]
    with ThreadPoolExecutor(max_workers=4) as e:
        result = list(e.map(lambda t: _calc_one_hour(t, latlon), times))
    print(result)

lat = 45.47
lon = 89.32
fr = 1638662400 - 3600 * 24
to = fr#1638669600 - 3600 - 3600
obtain(lat, lon, fr, to)

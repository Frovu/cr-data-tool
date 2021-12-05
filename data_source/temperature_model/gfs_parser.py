import requests
import logging
import pygrib
from datetime import datetime, timedelta
import numpy as np
import os
from scipy import interpolate, ndimage
from data_source.temperature_model.proxy import LEVELS
from concurrent.futures import ThreadPoolExecutor

_GFS_URL = 'https://nomads.ncep.noaa.gov'
_GFS_QUERY_VARS = '&var_TMP=on' + ''.join([f'&lev_{str(lvl)}_mb=on' for lvl in LEVELS])

def _download(filename, latlon, fcst_date, fcst_hour, source='gfs'):
    if source != 'gfs': source = 'gdas'
    hh, yyyymmdd = f'{fcst_date.hour:02}', fcst_date.strftime("%Y%m%d")
    query = f'/cgi-bin/filter_{source}_0p25.pl?'
    query += f'file={source}.t{hh}z.pgrb2.0p25.f{fcst_hour:03}'
    query += f'&dir=%2F{source}.{yyyymmdd}%2F{hh}%2Fatmos'
    query += f'&subregion=&leftlon={latlon[1][0]}&rightlon={latlon[1][1]}&bottomlat={latlon[0][0]}&toplat={latlon[0][1]}'
    logging.debug(f'Query GFS {source}.{yyyymmdd}+{fcst_hour:03}')
    res = requests.get(f'{_GFS_URL}{query}{_GFS_QUERY_VARS}', stream=True)
    if res.status_code == 200:
        with open(filename, 'wb') as f:
            for chunk in res.iter_content(1024):
                f.write(chunk)
        return filename
    return False

def _tries_list(dtime, depth=8, PER_H=6):
    tries = []
    age = datetime.now() - dtime
    fcst_date = dtime.replace(hour = dtime.hour // PER_H * PER_H)
    fcst_hour = dtime.hour % PER_H
    if age.days or age.seconds > 4*3600: # gdas is late for 3:45 hours at peak
        tries.append((fcst_date, fcst_hour, 'gdas'))
    for i in range(depth):
        tries.append((fcst_date, fcst_hour, 'gfs'))
        fcst_date -= timedelta(hours=PER_H)
        fcst_hour += PER_H
    return tries

# grid_margin determines size of queried subregion of coordinates (required for spline interp)
def _calc_one_hour(timestamp, lat, lon, grid_margin=2):
    result = np.empty(len(LEVELS))
    latlon = ( (lat - grid_margin, lat + grid_margin),
               (lon - grid_margin, lon + grid_margin) )
    dtime = datetime.utcfromtimestamp(timestamp)
    fname = dtime.strftime(f'tmp/gfs.{lat}.{lon}.%Y%m%d.%H.grb2')
    try:
        for args in _tries_list(dtime):
            if _download(fname, latlon, *args):
                grbs = pygrib.open(fname)
                lats, lons = grbs.message(1).latlons()
                lats, lons = lats[:,1], lons[1]
                lat_i = interpolate.interp1d(lats, np.arange(len(lats)))(lat)
                lon_i = interpolate.interp1d(lons, np.arange(len(lons)))(lon)
                grbs.rewind()
                for grb in grbs:
                    lvl = ndimage.map_coordinates(grb.values, ([lat_i], [lon_i]), mode='nearest')
                    result[LEVELS.index(grb.level)] = lvl
                break
            else:
                logging.warning(f'Can not get GFS, fcst_h={args[1]}')
    except:
        logging.error(f'Failed to get GFS data for {dtime}')
    if os.path.exists(fname): os.remove(fname)
    return result

def obtain(lat, lon, t_from, t_to, PERIOD=3600):
    times = [t for t in range(t_from, t_to + 1, PERIOD)]
    with ThreadPoolExecutor(max_workers=4) as e:
        result = list(e.map(lambda t: _calc_one_hour(t, lat, lon), times))
    print(result)

lat = 55.47
lon = 37.32
fr = 1638662400 + 12*3600#- 3600 * 24 * 4
to = fr + 20*3600
obtain(lat, lon, fr, to)

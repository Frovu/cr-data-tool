import os
from progressbar import ProgressBar
import numpy as np
from proxy import log
from ftplib import FTP
from netCDF4 import Dataset, num2date, date2index

def _extract_file(filename, lat, lon, start_time, end_time):
    data = Dataset(filename, 'r')
    print(data.title)
    print(", ".join([str(i) for i in data.variables["level"][:]]))
    assert "NMC reanalysis" in data.title
    air = data.variables["air"]
    times = data.variables["time"]
    print(end_time in num2date(times[:], units=times.units))
    lat_idx = np.where(data.variables["lat"][:] == lat)
    lon_idx = np.where(data.variables["lon"][:] == lon)
    start_idx = date2index(start_time, times)
    end_idx = date2index(end_time, times)
    print(f"lat={lat} lon={lon} from={start_time.date()}({start_idx}) to={end_time.date()}({end_idx})")
    for level_i, level in enumerate(data.variables["level"][:]):
        line = [a[level_i][lat][lon] for a in air[start_idx:end_idx]]
        print(f'{level}:\t{"  ".join([str("%.1f" % i) for i in line])}')

def _download_netcdf(year):
    fname = f'air.{year}.nc'
    ftp = FTP('ftp2.psl.noaa.gov')
    log.info('FTP login: '+ftp.login())
    ftp.cwd('Datasets/ncep.reanalysis/pressure')
    pbar = ProgressBar(maxval=ftp.size(fname))
    pbar.start()
    with open(os.path.join('tmp', fname), 'wb') as file:
        def write(data):
           file.write(data)
           nonlocal pbar
           pbar += len(data)
        ftp.retrbinary(f'RETR {fname}', write)
    log.info(f'Downloaded file {fname}')

# @params: date period to get data for
# @returns: 4d array [time][level][lat][lon]
def obtain(dt_start, dt_end):
    print("Missing intervals:")
    for period in missing_periods:
        print(f"\tfrom {period[0].ctime()}\n\t\tto {period[1].ctime()}")

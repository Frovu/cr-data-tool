import os
from progressbar import ProgressBar
import numpy as np
from proxy import log
from ftplib import FTP
from datetime import datetime
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

def _download(year):
    fname = f'air.{year}.nc'
    ftp = FTP('ftp2.psl.noaa.gov')
    log.debug('FTP login: '+ftp.login())
    log.info(f'Downloading file: {fname}')
    ftp.cwd('Datasets/ncep.reanalysis/pressure')
    pbar = ProgressBar(maxval=ftp.size(fname))
    pbar.start()
    with open(os.path.join('tmp', fname), 'wb') as file:
        def write(data):
           file.write(data)
           nonlocal pbar
           pbar += len(data)
        ftp.retrbinary(f'RETR {fname}', write)
    log.info(f'Downloaded file: {fname}')

# find out files downloads required to satisfy given interval
def _require_years(intervals):
    required = []
    current_year = datetime.now().year
    for interval in intervals:
        diff = interval[1].year - interval[0].year
        for i in range(diff + 1):
            year = interval[0].year + i
            if year in required: break # already required
            if year > current_year: break # no data for future
            fpath = os.path.join('tmp', f'air.{year}.nc')
            if not os.path.exists(fpath):
                required.append(year)
            else: # check that existing netcdf file is full and contains all required lines
                data = Dataset(fpath, 'r')
                times = data.variables["time"]
                if ((year == current_year and num2date(times[-1], units=times.units) <= interval[1])
                    or (year != current_year and times.size < (365*4))): # cant use '==' due to leap year
                    required.append(year)
    print(required)

# concurrently download all required files
def download_required_files(missing_intervals):
    threads = []
    for i in intervals: # spawn download/parse threads
        thread = Thread(target=lambda: queue.put(parser.obtain(i[0], i[1])))
        thread.start()
        threads.append(thread)
    for t in threads:
        t.join() # wait for all download/parse threads to finish

# @params: date period to get data for
# @returns: 4d array [time][level][lat][lon]
def obtain(dt_start, dt_end):
    print("Missing intervals:")
    for period in missing_periods:
        print(f"\tfrom {period[0].ctime()}\n\t\tto {period[1].ctime()}")

_require_years([[datetime.strptime('2016-01-01', '%Y-%m-%d'),
    datetime.strptime('2020-01-04', '%Y-%m-%d')]])

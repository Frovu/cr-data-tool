import os
from progressbar import ProgressBar
import numpy as np
from proxy import log
from ftplib import FTP
from datetime import datetime
from netCDF4 import Dataset, num2date, date2index
from threading import Thread

def _filename(year):
    return f'air.{year}.nc'

def _extract_from_file(year, start_time, end_time):
    fname = _filename(year)
    log.debug(f"Reading file: {fname} from {start_time.isoformat()} to {end_time.isoformat()}")
    data = Dataset(os.path.join('tmp', fname), 'r')
    assert "NMC reanalysis" in data.title
    times = data.variables["time"]
    #lat_idx = np.where(data.variables["lat"][:] == lat)
    #lon_idx = np.where(data.variables["lon"][:] == lon)
    start_idx = date2index(start_time, times)
    end_idx = date2index(end_time, times)
    #print(f"lat={lat} lon={lon} from={start_time.date()}({start_idx}) to={end_time.date()}({end_idx})")
    #for level_i, level in enumerate(data.variables["level"][:]):
    #line = [a[level_i][lat][lon] for a in air[start_idx:end_idx]]
        #print(f'{level}:\t{"  ".join([str("%.1f" % i) for i in line])}')
    return data.variables["air"][start_idx:end_idx]

def _download(year):
    fname = _filename(year)
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
            fpath = os.path.join('tmp', _filename(year))
            if not os.path.exists(fpath):
                required.append(year)
            else: # check that existing netcdf file is full and contains all required lines
                data = Dataset(fpath, 'r')
                times = data.variables["time"]
                if ((year == current_year and num2date(times[-1], units=times.units) <= interval[1])
                    or (year != current_year and times.size < (365*4))): # cant use '==' due to leap year
                    required.append(year)
    return required

# concurrently download all files required to fill specified intervals
def download_required_files(missing_intervals):
    to_download = _require_years(missing_intervals)
    threads = []
    for year in to_download: # spawn download/parse threads
        thread = Thread(target=_download, args=(year,))
        thread.start()
        threads.append(thread)
    for t in threads:
        t.join() # wait for all download/parse threads to finish

# Obtains data for interval !! Presumes all files are already downloaded !!
# @params: date period to get data for (should be 6h aligned!)
# @returns: 4d array [time][level][lat][lon]
def obtain(dt_start, dt_end):
    if dt_start.year == dt_end.year:
        return _extract_from_file(dt_start.year, dt_start, dt_end)
    # if several years are covered
    data_acc = _extract_from_file(dt_start.year, dt_start, datetime(dt_start.year, 12, 31, 18))
    for year in range(dt_start.year + 1, dt_end.year): # extract fully covered years
        data_acc += _extract_from_file(year, datetime(year, 1, 1, 0), datetime(year, 12, 31, 18))
    data_acc += _extract_from_file(dt_end.year, datetime(dt_end, 1, 1, 0), dt_end)
    return data_acc

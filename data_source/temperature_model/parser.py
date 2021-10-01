import os
import numpy as np
from data_source.temperature_model.proxy import log
from ftplib import FTP
from datetime import datetime, timedelta
from netCDF4 import Dataset, num2date, date2index
from threading import Thread

download_progress = 0
download_total = 0

if not os.path.exists('tmp'):
    os.makedirs('tmp')

def _filename(year):
    return f'air.{year}.nc'

def _extract_from_file(year, start_time, end_time):
    fname = _filename(year)
    log.debug(f"Reading file: {fname} from {start_time} to {end_time}")
    data = Dataset(os.path.join('tmp', fname), 'r')
    assert "NMC reanalysis" in data.title
    times = data.variables["time"]
    start_idx = date2index(start_time, times)
    end_idx = None if end_time >= num2date(times[-1], times.units) else date2index(end_time, times) + 1 # inclusive
    time_values = num2date(times[start_idx:end_idx], units=times.units)
    air = data.variables["air"][start_idx:end_idx]
    data.close()
    return time_values, air

def _download(year):
    fname = _filename(year)
    ftp = FTP('ftp2.psl.noaa.gov')
    log.debug('FTP login: '+ftp.login())
    log.info(f'Downloading file: {fname}')
    ftp.cwd('Datasets/ncep.reanalysis/pressure')
    global download_total
    download_total += ftp.size(fname)
    with open(os.path.join('tmp', fname), 'wb') as file:
        def write(data):
           file.write(data)
           global download_progress
           download_progress += len(data)
        ftp.retrbinary(f'RETR {fname}', write)
    log.info(f'Downloaded file: {fname}')

# find out files downloads required to satisfy given interval
def _require_years(intervals, delta):
    required = []
    current_year = datetime.now().year
    for interval in intervals:
        start = interval[0] - delta
        end = interval[1] + delta
        diff = end.year - start.year
        for i in range(diff + 1):
            year = start.year + i
            if year in required: continue # already required
            if year > current_year: break # no data for future
            fpath = os.path.join('tmp', _filename(year))
            if not os.path.exists(fpath):
                required.append(year)
            else: # check that existing netcdf file is full and contains all required lines
                try:
                    data = Dataset(fpath, 'r')
                    times = data.variables["time"]
                    if ((year == current_year and num2date(times[-1], times.units) <= interval[1] - timedelta(days=1))
                        or (year != current_year and times.size < (365*4))): # cant use '==' due to leap year
                        required.append(year)
                    data.close()
                except:
                    required.append(year)
    return required

# concurrently download all files required to fill specified intervals
def download_required_files(missing_intervals, delta):
    to_download = _require_years(missing_intervals, delta)
    log.debug(f'About to download: {to_download}')
    threads = []
    global download_total, download_progress
    download_progress = 0
    download_total = 0
    for year in to_download: # spawn download/parse threads
        thread = Thread(target=_download, args=(year,))
        thread.start()
        threads.append(thread)
    for t in threads:
        t.join() # wait for all download/parse threads to finish
    download_total = 0 # done

def get_download_progress():
    return None if download_total == 0 else round(download_progress / download_total, 2)

# Obtains data for interval !! Presumes all files are already downloaded !!
# @params: date period to get data for (should be 6h aligned!)
# @returns: 4d array [time][level][lat][lon]
def obtain(dt_start, dt_end):
    if dt_start.year == dt_end.year:
        return _extract_from_file(dt_start.year, dt_start, dt_end)
    # if several years are covered
    times, data = _extract_from_file(dt_start.year, dt_start, datetime(dt_start.year, 12, 31, 18))
    time_acc = [times]; data_acc = [data]
    for year in range(dt_start.year + 1, dt_end.year): # extract fully covered years
        times, data = _extract_from_file(year, datetime(year, 1, 1, 0), datetime(year, 12, 31, 18))
        time_acc.append(times)
        data_acc.append(data)
    times, data = _extract_from_file(dt_end.year, datetime(dt_end.year, 1, 1, 0), dt_end)
    time_acc.append(times)
    data_acc.append(data)
    return np.concatenate(time_acc), np.concatenate(data_acc)

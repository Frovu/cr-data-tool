
from ftplib import FTP
import logging, os
from threading import Thread
from datetime import datetime, timedelta, timezone

from temperature.interpolate import interpolate
from netCDF4 import Dataset, num2date, date2index
import numpy as np

log = logging.getLogger('crdt')
last_downloaded = [datetime(2000, 1, 1)]
download_progress = {}

PATH = 'data/ncep'

if not os.path.exists(PATH):
    os.makedirs(PATH)

def file_name(year):
	return f'air.{year}.nc'

def _download(year):
	fname = file_name(year)
	ftp = FTP('ftp2.psl.noaa.gov')
	log.debug('FTP login: %s', ftp.login())
	log.info(f'Downloading file: {fname}')
	ftp.cwd('Datasets/ncep.reanalysis/pressure')
	download_progress[year] = [0, ftp.size(fname)]
	if year == datetime.now().year:
		last_downloaded[0] = datetime.now()
	with open(os.path.join(PATH, fname), 'wb') as file:
		def write(data):
			file.write(data)
			download_progress[year][0] += len(data)
		ftp.retrbinary(f'RETR {fname}', write)
	log.info(f'Downloaded file: {fname}')

def _parse_file(fname, dt_from, dt_to):
	data = Dataset(os.path.join(PATH, fname), 'r')
	assert 'NMC reanalysis' in data.title
	log.debug(f'Reading: {fname} from {dt_from} to {dt_to}')
	times = data.variables['time']
	start_idx = date2index(dt_from, times)
	end_idx = None if dt_to >= num2date(times[-1], times.units) else date2index(dt_to, times) + 1 # inclusive
	time_values = num2date(times[start_idx:end_idx], units=times.units,
		only_use_cftime_datetimes=False, only_use_python_datetimes=True)
	epoch_times = np.array([dt.replace(tzinfo=timezone.utc).timestamp() for dt in time_values], dtype='f8')
	return np.column_stack((epoch_times, data.variables['air'][start_idx:end_idx]))

def ensure_downloaded(dt_interval):
	progress = {}
	now = datetime.now()
	for year in range(dt_interval[0].year, dt_interval[1].year + 1):
		progr = download_progress.get(year)
		value = progr and progr[0] / progr[1]
		print(year, value, year == now.year and now - last_downloaded[0] > timedelta(hours=2))
		if progr and value < 1:
			progress[year] = value
		elif (year == now.year and now - last_downloaded[0] > timedelta(hours=2)) \
				or not os.path.exists(os.path.join(PATH, file_name(year))):
			Thread(target=_download, args=(year,)).start()
			download_progress[year] = [0, 1]
			progress[year] = 0
	return progress if len(progress) > 0 else None

def obtain(dt_interval):
	pass
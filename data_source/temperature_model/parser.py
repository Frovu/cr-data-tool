import os
import numpy as np
import logging as log
from data_source.temperature_model.download import Downloader, filename
from datetime import datetime, timedelta, timezone
from netCDF4 import Dataset, num2date, date2index

if not os.path.exists('tmp'):
    os.makedirs('tmp')
downloader = Downloader()

def _extract_from_file(fname, dt_from, dt_to):
    data = Dataset(os.path.join('tmp', fname), 'r')
    assert "NMC reanalysis" in data.title
    log.debug(f"Reading: {fname} from {dt_from} to {dt_to}")
    times = data.variables["time"]
    start_idx = date2index(dt_from, times)
    end_idx = None if dt_to >= num2date(times[-1], times.units) else date2index(dt_to, times) + 1 # inclusive
    time_values = num2date(times[start_idx:end_idx], units=times.units,
        only_use_cftime_datetimes=False, only_use_python_datetimes=True)
    epoch_times = np.array([dt.replace(tzinfo=timezone.utc).timestamp() for dt in time_values], dtype=int)
    return epoch_times, data.variables["air"][start_idx:end_idx]

def _obtain_year(dt_from, dt_to, merge_query):
    try:
        year = dt_from.year
        fname = filename(year)
        res = _extract_from_file(fname, dt_from, dt_to)
    except:
        log.debug(f'Failed to read {fname}, downloading..')
        query = downloader.download(year)
        merge_query(query)
        query.await_result()
        res = _extract_from_file(fname, dt_from, dt_to)
    return res

# inclusive, presumes period to be aligned
def obtain(t_from, t_to, mq):
    dt_from, dt_to = [datetime.utcfromtimestamp(t) for t in [t_from, t_to]]
    if dt_from.year == dt_to.year:
        return _obtain_year(dt_from, dt_to, mq)
    times, data = _obtain_year(dt_from, datetime(dt_from.year, 12, 31, 18), mq)
    time_acc = [times]; data_acc = [data]
    for year in range(dt_from.year + 1, dt_to.year): # extract fully covered years
        times, data = _obtain_year(datetime(year, 1, 1, 0), datetime(year, 12, 31, 18), mq)
        time_acc.append(times)
        data_acc.append(data)
    times, data = _obtain_year(datetime(dt_to.year, 1, 1, 0), dt_to, mq)
    time_acc.append(times)
    data_acc.append(data)
    return np.concatenate(time_acc), np.concatenate(data_acc)

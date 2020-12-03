import numpy as np
from datetime import datetime, timedelta, time
import proxy
import parser
from threading import Thread
from queue import Queue

_lock = False

# receives 2d array a[lat][lon]
# returns value approximated for given coords
def _interpolate_coords(data, lat, lon):
    return data[0][0] # TODO

# receives 4d array a[time][level][lat][lon] (raw data)
# returns 2d array a[level][time] (approximated for given coords)
def _approximate_for_point(data, lat, lon):
    return data

# receives 2d array a[level][time]
def _interpolate_time(line, tick_min=60):
    return line

def _fill_gap(interval, lat, lon):
    # inteval time is 1h aligned, we should align it to data (6h)
    # we should also include some additional data for interpolation to complete
    # so we will actually allign it to days (ceil) and add one day to the end
    start_aligned = datetime.combine(interval[0], time())
    end_aligned = datetime.combine(interval[1], time()) + timedelta(days=1)
    log.debug(f"Processing interval for lat={lat} lon={lon} from {start_aligned.ctime()} to {end_aligned.ctime()}")
    data = parser.obtain(interval[0], interval[1])
    approximated = _approximate_for_point(data, lat, lon)
    result = [_interpolate_time(line) for line in approximated]
    # TODO: insert into sql
    log.debug(f"Interval processed for lat={lat} lon={lon}")

def _fill_all_gaps(missing_intervals, lat, lon):
    parser.download_required_files(missing_intervals) # this operation may take up to 10 minutes
    threads = []
    for i in intervals: # fill gaps concurrently
        thread = Thread(target=_fill_gap, args=(i, lat, lon))
        thread.start()
    for t in threads:
        t.join() # wait for all threads to finish
    log.debug("All intervals done")
    # release lock
    global _lock
    _lock = False

def get(lat, lon, start_time, end_time):
    lat = round(lat, 2)
    lon = round(lon, 2)
    missing_intervals = proxy.analyze_integrity(lat, lon, start_time, end_time)
    if not missing_intervals:
        return None
    elif len(missing_intervals) > 0:
        global _lock
        if _lock:
            return False # busy
        thread = Thread(target=_fill_all_gaps, args=(missing_intervals, lat, lon))
        _lock = True
        thread.start()
        return True # Accepted data processing query
    else:
        return proxy.select(lat, lon, start_time, end_time)

g = get(55.47, 37.32,
    datetime.strptime('2020-01-01', '%Y-%m-%d'),
    datetime.strptime('2020-01-02', '%Y-%m-%d'))

print(g)

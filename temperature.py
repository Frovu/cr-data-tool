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

# inteval time is 1h aligned, we should align it to data (6h), probably adding trailing 
def _fill_gap(interval, lat, lon):
    data = parser.obtain(interval[0], interval[1])
    log.debug(f"Interval processed for lat={lat} lon={lon} from {interval[0].ctime()} to {interval[1].ctime()}")

def _fill_all_gaps(missing_intervals):
    parser.download_required_files(missing_intervals) # this operation may take up to 10 minutes
    threads = []
    for i in intervals:
        thread = Thread(target=lambda: queue.put())
        thread.start()
    for t in threads:
        t.join() # wait for all threads to finish
    for interval in queue.queue:
        print(f"got interval of len {len(interval)}")
        # data = proxy.query(lat, lon, start_time, end_time)
        # approximated = _approximate_for_point(lat, lon)
        # result = [_interpolate_time(line) for line in approximated]
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
        thread = Thread(target=_fill_gaps, args=(missing_intervals, ))
        _lock = True
        thread.start()
        return True # Accepted data processing query
    else:
        return proxy.select(lat, lon, start_time, end_time)

g = get(55.47, 37.32,
    datetime.strptime('2020-01-01', '%Y-%m-%d'),
    datetime.strptime('2020-01-02', '%Y-%m-%d'))

print(g)

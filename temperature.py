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

def _fill_gaps(missing_intervals):
    threads = []
    queue = Queue()
    for i in intervals: # spawn download/parse threads
        thread = Thread(target=lambda: queue.put(parser.obtain(i[0], i[1])))
        thread.start()
    for t in threads:
        t.join() # wait for all download/parse threads to finish
    for interval in queue.queue:
        print(f"got interval of len {len(interval)}")
        # data = proxy.query(lat, lon, start_time, end_time)
        # approximated = _approximate_for_point(lat, lon)
        # result = [_interpolate_time(line) for line in approximated]
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

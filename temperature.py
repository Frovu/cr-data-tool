import numpy as np
from scipy import interpolate
from datetime import datetime, timedelta, time
import proxy
log = proxy.log
import parser
from threading import Thread

_lock = False

# receives 2d grid a[lat][lon]
# returns value approximated for given coords
def _approximate_coords(grid, lat, lon):
    return grid[0][0] # TODO

# receives 4d array a[time][level][lat][lon] (raw data)
# returns 2d array a[time][level] (approximated for given coords)
def _approximate_for_point(data, lat, lon):
    approximated = np.empty(data.shape[:2])
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            approximated[i][j] = _approximate_coords(data[i][j], lat, lon)
    return approximated

# receives 2d array a[time][level] with 6h res, returns it with 1h res
def _interpolate_time(times, data):
    inc = np.timedelta64(1, 'h')
    times_64 = np.array([np.datetime64(t) for t in times])
    new_times = np.arange(times_64[0], times_64[-1] + inc, inc)
    result = np.empty((len(new_times), data.shape[1]))
    for level_col in range(data.shape[1]): # interpolate each level separately
        old_line = data[:,level_col]
        spline = interpolate.splrep(times_64.astype('float64', casting='unsafe'), old_line, s=0)
        result[:,level_col] = interpolate.splev(new_times.astype('float64', casting='unsafe'), spline)
    return new_times.astype(datetime), result

def _fill_gap(interval, lat, lon, delta):
    log.debug(f"Obtaining interval for lat={lat} lon={lon} from {interval[0] - delta} to {interval[1] + delta}")
    times_6h, data = parser.obtain(interval[0] - delta, interval[1] + delta)
    log.debug(f"Interval retrieved, len={len(data)}")
    approximated = _approximate_for_point(data, lat, lon)
    log.debug(f"Interval approximated for lat={lat} lon={lon}")
    times_1h, result = _interpolate_time(times_6h, approximated)
    log.debug(f"Interval interpolated for time, len={times_1h.size}")
    # We will not insert edges data so result should be trimmed
    # also proxy.insert requires array of (time, p_...)
    trim_from = np.nonzero(times_1h == interval[0])[0][0]
    trim_to = np.nonzero(times_1h == interval[1])[0][0] + 1 # inclusive
    rows = [([times_1h[i]] + list(result[i])) for i in range(trim_from, trim_to)]
    proxy.insert(rows, lat, lon)
    log.debug(f"Interval inserted")

# intevals time is 1h aligned, we should align it to data (6h)
def _align_intervals(intervals):
    aligned = []
    for interval in intervals:
        start = datetime.combine(interval[0], time(interval[0].hour // 6 * 6))
        end = datetime.combine(interval[1], time(interval[1].hour // 6 * 6))
        if interval[1].hour % 6 != 0: # include not even trail
            end += timedelta(hours=6)
        aligned.append((start, end))
    return aligned

# we should query some additional data on the edges for smooth spline
# so we will query interval +- 1 day
def _fill_all_gaps(missing_intervals, lat, lon):
    aligned_intervals = _align_intervals(missing_intervals)
    delta = timedelta(days=1)
    parser.download_required_files(aligned_intervals, delta) # this operation may take up to 10 minutes
    threads = []
    log.debug(f"About to fill {len(aligned_intervals)} interval(s)")
    for i in aligned_intervals: # fill gaps concurrently
        thread = Thread(target=_fill_gap, args=(i, lat, lon, delta))
        thread.start()
        threads.append(thread)
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
        return proxy.select(lat, lon, start_time, end_time)
    # data processing required
    global _lock
    if _lock:
        return False # busy
    thread = Thread(target=_fill_all_gaps, args=(missing_intervals, lat, lon))
    _lock = True
    thread.start()
    return True # Accepted data processing query

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
    approximated = []
    for levels_line in data:
        new_line = []
        for coords_grid in levels_line:
            approx = _approximate_coords(coords_grid, lat, lon)
            new_line.append(approx)
        approximated.append(new_line)
    return approximated

# receives 2d array a[time][level] with 6h res, returns it with 1h res
def _interpolate_time(times, data):
    result = np.empty(np.flip(data.shape))
    # create new times axis
    inc = timedelta(hours=1)
    new_times = np.arange(times[0], times[-1] + inc, inc)
    for level_col in range(data.shape[1]): # interpolate each level separately
        old_line = data[:,level_col]
        spline = interpolate.splrep(times, old_line, s=0) #.astype('datetime64')
        result[:,level_col] = interpolate.splev(new_times, spline)
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
    trim_from = np.nonzero(times_1h == interval[0])
    trim_to = np.nonzero(times_1h == interval[1])
    rows = [[times_1h[i]] + result[i] for i in range(trim_from, trim_to)]
    proxy.insert(rows, lat, lon)
    log.debug(f"Interval inserted")

# intevals time is 1h aligned, we should align it to data (6h)
def _align_intervals(intervals):
    aligned = []
    for interval in intervals:
        start = datetime.combine(interval[0], time(interval[0].hour // 6 * 6))
        inc_end = 0 if interval[1].hour % 6 == 0 else 6
        end = datetime.combine(interval[1], time(interval[1].hour // 6 * 6 + inc_end)) # +1 to include not even trail
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
    log.debug(f"Queried for lat={lat} lon={lon} from {start_time.isoformat()} to {end_time.isoformat()} ")
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

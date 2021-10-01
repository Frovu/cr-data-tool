from datetime import datetime, timezone
import logging as log
import requests
import numpy
import json
import traceback
from math import floor, ceil
import data_source.stations_meteo.db_proxy as proxy

AWS_RMP_PAGE = 24*6 # aws.rmp seems to restrict max resp size by something like 6.5 days of data
AWS_RMP_IDX = {
    'Moscow': '91001'
}
progress_total = 0
progress_current = 0

def _query_aws_rmp(index, dt_from, dt_to):
    try:
        r = requests.post('http://213.171.38.44:27416/aws.rmp/users/php/getSOAPMeteo.php', data = {
            'index': index,
            'dtFrom': dt_from,
            'dtTo': dt_to
        })
    except:
        return None
    if r.status_code != 200: return None
    return json.loads(r.text.encode().decode('utf-8-sig'))

# TODO: introduce spline interpolation for proper alignment if accuracy required
def _align_to_period(datasets, period):
    if len(datasets.keys()) < 1: return []
    dt_from = datasets[next(iter(datasets))][0][0]
    dt_to = 0
    for ser in datasets:
        if datasets[ser][0][0] < dt_from:
            dt_from = datasets[ser][0][0]
        if datasets[ser][0][-1] > dt_to:
            dt_to = datasets[ser][0][-1]
    # print('  got', datetime.utcfromtimestamp(dt_from), 'to', datetime.utcfromtimestamp(dt_to))
    dt_from = period * floor(dt_from / period)
    dt_to = period * ceil(dt_to / period)
    keys = list(datasets.keys())
    pressure = keys.index('pressure') if 'pressure' in keys else -1
    res_len = ceil((dt_to-dt_from)/period)
    dtype = [('time', datetime)] + [(f'd{i}', float) for i in range(len(keys))]
    data = numpy.empty(res_len, dtype=dtype)
    times = [datasets[k][0] for k in keys]
    values = [datasets[k][1] for k in keys]
    si = [0 for k in keys]
    lens = [len(times[i]) for i in range(len(keys))]
    period_start = dt_from
    for res_i in range(res_len):
        period_end = period_start + period
        data[res_i][0] = datetime.utcfromtimestamp(period_start)
        for i in range(len(keys)):
            acc = 0
            cnt = 0
            if si[i] >= lens[i]:
                data[res_i][i+1] = None
                continue
            while times[i][si[i]] < period_end:
                acc += values[i][si[i]]
                cnt += 1
                si[i] += 1
                if si[i] >= lens[i]: break
            if i == pressure:
                acc /= 100
            # print("  "*i, datetime.utcfromtimestamp(period_start), cnt)
            data[res_i][i+1] = round(acc / cnt, 2) if cnt > 0 else None
        period_start += period
    return data

def _obtain_from_aws_rmp(station, time_range, query, period=3600):
    index = AWS_RMP_IDX[station]
    epoch_range = [int(t.replace(tzinfo=timezone.utc).timestamp()) for t in time_range]
    epoch_range[0] -= period
    epoch_range[1] += period
    pages = range(epoch_range[0], epoch_range[1], AWS_RMP_PAGE*period)
    global progress_total, progress_current
    progress_total = len(pages)
    for dt_from in pages:
        dt_to = dt_from + AWS_RMP_PAGE*period
        if dt_to > epoch_range[1]:
            dt_to = epoch_range[1]
        # print('query', datetime.utcfromtimestamp(dt_from), 'to', datetime.utcfromtimestamp(dt_to))
        raw_data = _query_aws_rmp(index, dt_from, dt_to)
        if raw_data is None:
            log.error(f'Failed to obtain, aborting aws.rmp: {station} {dt_from}:{dt_to}');
            return None
        data = dict()
        for entry in raw_data:
            if not (type(entry) is dict):
                continue
            sensor = entry.get('0', {}).get('sensor_name')
            if sensor is None:
                continue
            value = entry.get('value', [])
            if 't2' in query and 'HMP155' == sensor:
                if len(value) < 1 or value[0] < 200: # weird check that this is actually temperature in Kelvins (not humidity)
                    continue
                data['t2'] = (entry.get('time', []), value)
            elif 'pressure' in query and 'BARO-1/MD-20Д' == sensor:
                data['pressure'] = (entry.get('time', []), value)
        aligned = _align_to_period(data, period)
        log.info(f'aws.rmp: {station} <- [{len(aligned)}] from {datetime.utcfromtimestamp(dt_from)}')
        proxy.insert(aligned, list(data.keys()), station)
        progress_current += 1
    progress_total = progress_current = 0

def get_progress():
    return round(progress_current / progress_total, 2) if progress_total else 1

def fill_interval(station, time_range, query):
    try:
        if station == 'Moscow':
            return _obtain_from_aws_rmp(station, time_range, query)
        else:
            return None
    except Exception:
        log.error(f'Exception in stations_meteo.parser.obtain: {traceback.format_exc()}')
        return False
    finally:
        return True

def supported(station):
    return station in ['Moscow']

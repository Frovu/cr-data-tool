from datetime import datetime, timezone
import logging as log
import requests
import numpy
import json
from math import floor, ceil
import data_source.stations_meteo.db_proxy as proxy

AWS_RMP_PAGE = 8196
AWS_RMP_IDX = {
    'Moscow': '91001'
}

def query_aws_rmp(index, dt_from, dt_to):
    r = requests.post('http://213.171.38.44:27416/aws.rmp/users/php/getSOAPMeteo.php', data = {
        'index': index,
        'dtFrom': dt_from,
        'dtTo': dt_to
    })
    if r.status_code != 200: return None
    return json.loads(r.text.encode().decode('utf-8-sig'))

# TODO: introduce spline interpolation for proper alignment if accuracy required
def align_to_period(datasets, period):
    dt_from = datasets[next(iter(datasets))][0][0]
    dt_to = 0
    for ser in datasets:
        if datasets[ser][0][0] < dt_from:
            dt_from = datasets[ser][0][0]
        if datasets[ser][0][-1] > dt_to:
            dt_to = datasets[ser][0][-1]
    dt_from = period * floor(dt_from / period)
    dt_to = period * ceil(dt_to / period)
    keys = list(datasets.keys())
    pressure = keys.index('pressure') if 'pressure' in keys else -1
    res_len = ceil((dt_to-dt_from)/period)
    data = numpy.empty([res_len, (1 + len(keys))], dtype=numpy.float32)
    times = [datasets[k][0] for k in keys]
    values = [datasets[k][1] for k in keys]
    si = [0 for k in keys]
    lens = [len(times[i]) for i in range(len(keys))]
    period_start = dt_from
    for res_i in range(res_len):
        period_end = period_start + period
        data[res_i][0] = period_start
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
            data[res_i][i+1] = (acc / cnt) if cnt > 0 else None
        period_start += period
    print(data)
    return data

def obtain_from_aws_rmp(station, time_range, query, period=3600):
    index = AWS_RMP_IDX[station]
    epoch_range = [int(t.replace(tzinfo=timezone.utc).timestamp()) for t in time_range]
    for dt_from in range(epoch_range[0], epoch_range[1], AWS_RMP_PAGE*period):
        dt_to = dt_from + AWS_RMP_PAGE*period
        if dt_to > epoch_range[1]:
            dt_to = epoch_range[1]
        raw_data = query_aws_rmp(index, dt_from, dt_to)
        if raw_data is None:
            log.error(f'Failed to obtain aws.rmp: {station} {dt_from}:{dt_to}');
            continue
        data = dict()
        for entry in raw_data:
            sensor = entry.get('0', {}).get('sensor_name')
            value = entry.get('value', [])
            if sensor is None:
                continue
            if 'HMP155' == sensor:
                if len(value) < 1 or value[0] < 200: # weird check that this is actually temperature in Kelvins (not humidity)
                    continue
                data['t2'] = (entry.get('time', []), value)
            elif 'BARO-1/MD-20Д' == sensor:
                data['pressure'] = (entry.get('time', []), value)
        for col in ['t2', 'pressure']:
            if col not in data:
                log.error(f'Data for \'{col}\' is missing in aws.rmp: {station} {dt_from}:{dt_to}');
        aligned = align_to_period(data, period)
        log.info(f'aws.rmp:{station} <- [{len(aligned)}] from {time_range[0]} to {time_range[1]}')
        proxy.insert(aligned, list(data.keys()), station)


def query(station, time_range, query):
    if station == 'Moscow':
        return obtain_from_aws_rmp(station, time_range, query)
    else:
        return None

dt_strt = datetime(2021, 9, 26, 23, 48)
dt_end = datetime(2021, 9, 27, 23, 58)
query('Moscow', [dt_strt, dt_end], ['t2'])

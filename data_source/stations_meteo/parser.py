from datetime import datetime, timezone
import logging as log
import requests
import numpy
import json
import traceback
from math import floor, ceil
import data_source.stations_meteo.db_proxy as proxy

# aws.rmp seems to restrict max resp size by something like 6.5 days of data
AWS_RMP_THRESHOLD = 6*24*3600
AWS_RMP_IDX = {
    'Moscow': '91001'
}

def _query_aws_rmp(index, t_from, t_to):
    try:
        r = requests.post('http://213.171.38.44:27416/aws.rmp/users/php/getSOAPMeteo.php', data={
            'index': index,
            'dtFrom': t_from,
            'dtTo': t_to
        }, timeout=30)
    except:
        return None
    if r.status_code != 200: return None
    return json.loads(r.text.encode().decode('utf-8-sig'))

# TODO: introduce spline interpolation for proper alignment if accuracy required
def _align_to_period(datasets, t_from, t_to, period):
    for ser in datasets:
        if datasets[ser][0][0] < t_from:
            t_from = datasets[ser][0][0]
        if datasets[ser][0][-1] > t_to:
            t_to = datasets[ser][0][-1]
    t_from = period * floor(t_from / period)
    t_to = period * ceil(t_to / period)
    keys = list(datasets.keys())
    pressure = keys.index('pressure') if 'pressure' in keys else -1
    res_len = ceil((t_to-t_from)/period)
    data = numpy.empty([res_len, len(keys)+1], dtype='O')
    times = [datasets[k][0] for k in keys]
    values = [datasets[k][1] for k in keys]
    si = [0 for k in keys]
    lens = [len(times[i]) for i in range(len(keys))]
    period_start = t_from
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
            # print("  "*i, datetime.utcfromtimestamp(period_start), cnt)
            data[res_i][i+1] = round(acc / cnt, 2) if cnt > 0 else None
        period_start += period
    return data.tolist()

def _obtain_rmp_interval(station, t_from, t_to, query, period, hopeless=True):
        raw_data = _query_aws_rmp(AWS_RMP_IDX[station], t_from, t_to)
        if raw_data is None:
            log.error(f'Failed to obtain, aborting aws.rmp: {station} {t_from}:{t_to}');
            raise Exception('abort aws.rmp')
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
        if len(data.keys()) > 0:
            aligned = _align_to_period(data, t_from, t_to, period)
            proxy.insert(station, aligned, list(data.keys()))
        elif hopeless:
            proxy.fill_empty(station, t_from, t_to, period)

def get_tasks(station, period, fill_fn, query=['t2', 'pressure']):
    intg_fn = lambda i: proxy.analyze_integrity(station, *i)
    if station == 'Moscow':
        def proc_fn(i):
            _obtain_rmp_interval(station, *i, query, period)
    assert proc_fn
    return [('local meteo', fill_fn, (intg_fn, proc_fn, True, 4, AWS_RMP_THRESHOLD//period))]

def supported(station):
    return station in ['Moscow']

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import requests, json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import numpy as np
import time
import os

import matplotlib.pyplot as plt
plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['figure.facecolor'] = 'darkgrey'

url = 'https://crst.izmiran.ru/crdt'
# url = 'http://localhost:5000'

PERIOD = 365*2 # days
session = requests.Session()

def _obtain_coef(dt_from, dt_to, station, channel, single):
    tfr, tto = [int(d.replace(tzinfo=timezone.utc).timestamp()) for d in (dt_from, dt_to)]
    par = f'from={tfr}&to={tto}&station={station}&channel={channel}&against={"Tm" if single else "all"}&only=coef'
    uri = f'{url}/api/muones/correlation?{par}'
    while True:
        res = session.get(uri, verify=False)
        if res.status_code != 200:
            print(f'request failed: {res.status_code}')
            return None, None
        body = json.loads(res.text)
        status, data = body['status'], body.get('data')
        assert status != 'failed'
        if status != 'ok':
            print(f'{dt_from}: {status} {body.get("info") or ""}')
            time.sleep(3)
        else:
            return dt_from, data.get('coef' if single else 'coef_temperature') or np.nan, data.get('error') if single else 0

def obtain(station: str, channel: str, dt_from: datetime, dt_to: datetime,
period: timedelta=timedelta(days=365), single: bool=False):
    print(f'obtaining {station}/{channel}')
    periods = [dt_from+timedelta(n) for n in range(0, (dt_to-dt_from).days, period.days)]
    _func = lambda start: _obtain_coef(start, start+period, station, channel, single)
    with ThreadPoolExecutor(max_workers=16) as executor:
        data = np.array(list(executor.map(_func, periods)))
    return data[:,0], data[:,1], data[:,2]

if __name__ == '__main__':
    tfr = datetime(1986, 4, 1)
    tto = datetime(2018, 12, 31)
    fig, ax = plt.subplots()
    channels = ['N', 'N2', 'N3']
    colors = ['#00FFAA', '#00AAFF', '#ccFF00', '#55FF00']

    def _plot_one(channel):
        times, coef, err = obtain('Nagoya', channel, tfr, tto, timedelta(days=PERIOD))
        color = colors[channels.index(channel)]
        ax.errorbar(times, coef, err, fmt=f'-', color=color, ecolor='magenta', label=f't_coef :{channel}')

    start = time.time()
    # with ThreadPoolExecutor(max_workers=4) as executor:
    #     executor.map(_plot_one, channels)
    for c in channels:
        _plot_one(c)
    print('done in', round(time.time() - start, 2), 'seconds')

    # times, coef, err = obtain('Nagoya', 'V', tfr, tto, timedelta(days=PERIOD), single=True)
    # coef /= -100
    # err /= -100
    # ax.errorbar(times, coef, err, fmt=f'-', color='#FFAA00', ecolor='magenta', label=f't_coef :V (single)')

    legend = plt.legend()
    plt.title(f'period={PERIOD} days')
    plt.setp(legend.get_texts(), color='grey')
    plt.show()

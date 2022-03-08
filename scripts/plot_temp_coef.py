from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import requests, json
import numpy as np
import time
import os

import matplotlib.pyplot as plt
plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['figure.facecolor'] = 'darkgrey'

url = 'https://crst.izmiran.ru/crdt'
url = 'http://localhost:5000'

def _login():
    session = requests.Session()
    login = os.environ.get('CRDT_LOGIN')
    passwd = os.environ.get('CRDT_PASS')
    res = session.post(f'{url}/api/auth/login', data={
        'login': login,
        'password': passwd
    }, verify=False)
    assert res.status_code == 200
    res = session.get(f'{url}/api/auth/login')
    return session

def _obtain_coef(dt_from, dt_to, station, channel, session):
    tfr, tto = [int(d.replace(tzinfo=timezone.utc).timestamp()) for d in (dt_from, dt_to)]
    par = f'from={tfr}&to={tto}&station={station}&channel={channel}&against=Tm&only=coef'
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
            print(f'{dt_from}: {status}')
            time.sleep(3)
        else:
            return dt_from, data.get('coef'), data.get('error')

def plot(station: str, channel: str,
dt_from: datetime, dt_to: datetime, period: timedelta=timedelta(days=365)):
    session = _login()
    periods = [dt_from+timedelta(n) for n in range(0, (dt_to-dt_from).days, period.days)]
    _func = lambda start: _obtain_coef(start, start+period, station, channel, session)
    with ThreadPoolExecutor(max_workers=4) as executor:
        data = np.array(list(executor.map(_func, periods)))
    print(data)
    time, coef, err = data[:,0], data[:,1], data[:,2]
    fig, ax = plt.subplots()
    ax.errorbar(time, coef, err, fmt='c-', ecolor='red')
    plt.show()

if __name__ == '__main__':
    tfr = datetime(1995, 1, 5)
    tto = datetime(2012, 1, 5)
    plot('Nagoya', 'V', tfr, tto)

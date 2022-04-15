from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import numpy as np
import time, os, logging

import matplotlib.pyplot as plt
plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['figure.facecolor'] = 'darkgrey'

import data_source.muones.data as muon

PERIOD = 365*2

start = time.time()
tfr = datetime(2004, 1, 1)
tto = datetime(2005, 12, 31)
t_from, t_to = [a.replace(tzinfo=timezone.utc).timestamp() for a in [tfr, tto]]

while True:
    status, info = muon._get_prepare('Nagoya', t_from, t_to, 3600, 'V', ['T_m', 'T_eff'])
    if status == 'ok':
        data = np.array(muon.proxy.select(*info, ['T_m', 'T_eff'])[0])
        times, t_m, t_eff = data[:,0], data[:,1], data[:,2]
        break
    else:
        time.sleep(1)

fig, ax = plt.subplots()
channels = ['S', 'E', 'V']
colors = ['#00FFAA', '#00AAFF', '#ccFF00', '#55FF00']

times = [datetime.utcfromtimestamp(t) for t in times]
ax.plot(times, t_m, color=colors[0], label=f't_m')
ax.plot(times, t_eff, color=colors[2], label=f't_eff')



print('done in', round(time.time() - start, 2), 'seconds')
legend = plt.legend()
plt.title(f'period={PERIOD} days')
plt.setp(legend.get_texts(), color='grey')
plt.show()

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import numpy as np
import time, os, logging

import matplotlib.pyplot as plt
plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['figure.facecolor'] = 'darkgrey'

import data_source.muones.data as muon
import data_source.temperature_model.temperature as temperature

PERIOD = 365*2

start = time.time()
tfr = datetime(2004, 1, 1)
tto = datetime(2005, 12, 30)
t_from, t_to = [a.replace(tzinfo=timezone.utc).timestamp() for a in [tfr, tto]]

while True:
    status, info = muon._get_prepare('Nagoya', t_from, t_to, 3600, 'V', ['T_eff'])
    if status == 'ok':
        data = np.array(muon.proxy.select(*info, ['T_m', 'T_eff'])[0])
        t_times, t_m, t_eff = data[:,0], data[:,1], data[:,2]
        break
    else:
        time.sleep(1)


t_data = muon.corrections._t_obtain_model(info[0], t_from, t_to, lambda x: None, temperature.proxy.LEVELS_COLUMNS[::-1])


fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)



colors = ['#00FFAA', '#00AAFF', '#ccFF00', '#55FF00']


t_times = [datetime.utcfromtimestamp(t) for t in t_times]
ax1.plot(t_times, t_m, color=colors[1], label=f't_m')
ax1.plot(t_times, t_eff, color=colors[2], label=f't_eff')
twx = ax1.twinx()
twx.plot(t_times, t_m-t_eff, color=colors[0], linewidth=0.2, label=f'diff')
ax1.set_title('temperature, K')
plt.setp(ax1.legend().get_texts(), color='grey')

# res_eff = muon.corrections.corrected(*info, 'recalc', 'T_eff')
# res_ma = muon.corrections.corrected(*info, 'recalc', 'T_m')
# corr_eff = np.array(res_eff[0])
# corr_ma = np.array(res_ma[0])
# c_ma_t = [datetime.utcfromtimestamp(t) for t in corr_ma[:,0]]
# c_ef_t = [datetime.utcfromtimestamp(t) for t in corr_eff[:,0]]
# v_ma = corr_ma[:,1] / np.mean(corr_ma[:,1]) - 1
# v_ef = corr_eff[:,1] / np.mean(corr_eff[:,1]) - 1
# ax3.plot(c_ma_t, v_ma*100, linewidth=0.5, color=colors[1], label=f'corr_mass_avg')
# ax3.plot(c_ef_t, v_ef*100, linewidth=0.5, color=colors[2], label=f'corr_effective')
# ax3.set_title('corrected variation ()')
# plt.setp(ax3.legend().get_texts(), color='grey')

# data = np.array(muon.proxy.select(*info, ['source', 'T_eff'], where='source>0', include_time=False)[0])
# vv = data[:,0] / np.mean(data[:,0]) - 1
# ax4.scatter(data[:,1], vv*100, c=colors[2], marker='.', s=4, label='v(T_eff)')
# plt.setp(ax4.legend().get_texts(), color='grey')

legend = plt.legend()
# plt.title(f'period={PERIOD} days')
plt.setp(legend.get_texts(), color='grey')
print('plot in', round(time.time() - start, 2), 'seconds')
plt.show()

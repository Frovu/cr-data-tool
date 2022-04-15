from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from sklearn.linear_model import LinearRegression
import numpy as np
import time, os, logging

import matplotlib.pyplot as plt
plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['figure.facecolor'] = 'darkgrey'

import data_source.muones.data as muon
import data_source.temperature_model.temperature as temperature

PERIOD = 365*2

start = time.time()
tfr = datetime(2000, 1, 1)
tto = datetime(2004, 12, 30)
t_from, t_to = [a.replace(tzinfo=timezone.utc).timestamp() for a in [tfr, tto]]

ST = 'Nagoya'
CH = 'V'

while True:
    status, info = muon._get_prepare(ST, t_from, t_to, 3600, CH, ['T_eff'])
    if status == 'ok':
        data = np.array(muon.proxy.select(*info, ['T_m', 'T_eff'])[0])
        t_times, t_m, t_eff = data[:,0], data[:,1], data[:,2]
        break
    else:
        time.sleep(1)

data = np.array(muon.proxy.select(*info, ['source', 'pressure'], where='source>0')[0])
times, raw, pressure = data[:,0], data[:,1], data[:,2]
pr = np.mean(pressure) - pressure
t_data = muon.corrections._t_obtain_model(info[0], t_from, t_to, lambda x: None, temperature.proxy.LEVELS_COLUMNS[::-1])
t_data = t_data[np.in1d(t_data[:,0], times),1:]
t_vars = np.mean(t_data, axis=0) - t_data
gsm_result = np.column_stack(muon.corrections.gsm.get_variation(*info))
gsm_result = gsm_result[np.in1d(gsm_result[:,0], times),1:]
regr_data = np.column_stack((pr, gsm_result, t_vars))
regr = LinearRegression().fit(regr_data, np.log(raw))
lvl_coefs = regr.coef_[3:]
m_corrected = raw * np.exp(-1 * regr.coef_[0] * pr)
for i in range(len(lvl_coefs)):
    m_corrected *= 1 - lvl_coefs[i] * t_vars[:,i]
v_m_corrected = m_corrected / np.mean(m_corrected) - 1
times = [datetime.utcfromtimestamp(t) for t in times]

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, gridspec_kw={'width_ratios': [3, 1], 'height_ratios': [1, 2]})

colors = ['#00FFAA', '#00AAFF', '#ccFF00', '#50FF00']


t_times = [datetime.utcfromtimestamp(t) for t in t_times]
ax1.plot(t_times, t_m, color=colors[1], label=f't_m')
ax1.plot(t_times, t_eff, color=colors[2], label=f't_eff')
plt.setp(ax1.legend().get_texts(), color='grey')
twx = ax1.twinx()
twx.plot(t_times, t_m-t_eff, color=colors[0], linewidth=0.2)
ax1.set_title('temperature, K')

res_eff = muon.corrections.corrected(*info, 'recalc', 'T_eff')
res_ma = muon.corrections.corrected(*info, 'recalc', 'T_m')
corr_eff = np.array(res_eff[0])
corr_ma = np.array(res_ma[0])
c_ma_t = [datetime.utcfromtimestamp(t) for t in corr_ma[:,0]]
c_ef_t = [datetime.utcfromtimestamp(t) for t in corr_eff[:,0]]
v_ma = corr_ma[:,1] / np.mean(corr_ma[:,1]) - 1
v_ef = corr_eff[:,1] / np.mean(corr_eff[:,1]) - 1
v_src = corr_eff[:,2] / np.mean(corr_eff[:,2]) - 1
v_gsm = corr_eff[:,6] + corr_eff[:,7]
ax3.plot(c_ma_t, v_ma*100, linewidth=0.4, color=colors[1], label=f'corr_mass_avg')
ax3.plot(c_ef_t, v_ef*100, linewidth=0.4, color=colors[2], label=f'corr_effective')
ax3.plot(times, v_m_corrected*100, linewidth=0.4, color=colors[3], label=f'corr_multi')
ax3.plot(c_ef_t, v_src*100, linewidth=0.2, color='#8800aa', label=f'uncorrected')
twx = ax3.twinx()
twx.plot(c_ef_t, v_gsm, linewidth=0.3, color='#00ffff', label=f'gsm_v')
ax3.set_title(f'corrected variation (c_eff={round(res_eff[2]["coef_temperature"]*1000,2)}, c_ma={round(res_ma[2]["coef_temperature"]*1000,2)})')
plt.setp(ax3.legend().get_texts(), color='grey')
plt.setp(twx.legend().get_texts(), color='grey')

data = np.array(muon.proxy.select(*info, ['source', 'T_m'], where='source>0', include_time=False)[0])
vv = data[:,0] / np.mean(data[:,0]) - 1
ax4.scatter(data[:,1], vv*100, c=colors[1], marker='.', s=3, label='v(T_m)')
twx = ax4.twiny()
data = np.array(muon.proxy.select(*info, ['source', 'T_eff'], where='source>0', include_time=False)[0])
twx.scatter(data[:,1], vv*100, c=colors[2], marker='.', s=3, label='v(T_eff)')
plt.setp(ax4.legend().get_texts(), color='grey')
plt.setp(twx.legend().get_texts(), color='grey')
ax4.set_title('correlation')

levels = muon.corrections.LEVELS
W = muon.corrections.TEMP_EFF_WEIGHT[(info[0].station_name, info[0].angle)]
ax2.plot(levels, W, color=colors[2], label=f't_eff')
twx = ax2.twinx()
twx.plot(temperature.LEVELS[::-1], lvl_coefs*1000, color=colors[3], label=f't_multi')
plt.setp(ax2.legend().get_texts(), color='grey')
plt.setp(twx.legend().get_texts(), color='grey')
ax2.set_title('weight distribution')

legend = plt.legend()
plt.suptitle(f'{ST}:{CH}')
plt.setp(legend.get_texts(), color='grey')
print('plot in', round(time.time() - start, 2), 'seconds')
plt.show()

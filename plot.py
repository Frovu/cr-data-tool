import temperature
import parser
import logging
import time as tm
logging.disable(logging.DEBUG)
import matplotlib.pyplot as plt
logging.disable(logging.NOTSET)
from datetime import datetime, timedelta, time
plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['figure.facecolor'] = 'darkgrey'

def plot(times, level, label=None):
    logging.disable(logging.DEBUG)
    fig, ax = plt.subplots()
    ax.plot(times, level, 'c')
    node_level = [level[i] for i in range(0, len(times), 6)]
    node_date = [times[i] for i in range(0, len(times), 6)]
    ax.plot(node_date, node_level, 'r.')
    legend = plt.legend([label or 'temp'])
    plt.setp(legend.get_texts(), color='grey')
    plt.show()

def query_and_plot(lat, lon, dt_from, dt_to):
    status, data = temperature.get(lat, lon, dt_from, dt_to)
    while status != 200:
        print(f"status: {status} waiting 2s")
        tm.sleep(2)
        status, data = temperature.get(lat, lon, dt_from, dt_to)
    times = [a[0] for a in data]
    level = [a[1] for a in data]
    plot(times, level, 't at 1000 mb')

dt_strt = datetime(2017, 2, 1)
dt_end = datetime(2020, 11, 1)
query_and_plot(55.47, 37.32, dt_strt, dt_end)

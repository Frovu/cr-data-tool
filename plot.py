import data_source.temperature_model.temperature as temperature
import logging
import time as tm
logging.disable(logging.DEBUG)
import matplotlib.pyplot as plt
logging.disable(logging.NOTSET)
from datetime import datetime, timedelta, time
plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['figure.facecolor'] = 'darkgrey'

# LEVELS = [1000.0, 925.0, 850.0, 700.0, 600.0, 500.0, 400.0, 300.0, 250.0, 200.0,
# 150.0, 100.0, 70.0, 50.0, 30.0, 20.0, 10.0]

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

def query_and_plot(level, lat, lon, dt_from, dt_to):
    level_id = temperature.proxy.LEVELS.index(level)
    status, data = temperature.get(lat, lon, dt_from, dt_to)
    while status != 200:
        print(f"status: {status} waiting 5s")
        tm.sleep(5)
        status, data = temperature.get(lat, lon, dt_from, dt_to)
    times = [a[0] for a in data]
    levels = [a[level_id + 1] for a in data]
    plot(times, levels, f't at {level} mb')

dt_strt = datetime(2021, 8, 1)
dt_end = datetime(2022, 6, 1)
query_and_plot(1000, 55.47, 37.32, dt_strt, dt_end)

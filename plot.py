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

def fetch():
    temperature.get(55.47, 37.32, datetime.strptime('2020-01-3', '%Y-%m-%d'), datetime.strptime('2020-01-4', '%Y-%m-%d'))
    tm.sleep(1.5)
    temperature.get(55.47, 37.32, datetime.strptime('2020-01-7', '%Y-%m-%d'), datetime.strptime('2020-01-8', '%Y-%m-%d'))
    tm.sleep(1.5)
    temperature.get(55.47, 37.32, datetime.strptime('2020-01-1', '%Y-%m-%d'), datetime.strptime('2020-01-10', '%Y-%m-%d'))
    tm.sleep(1.5)
#fetch()

dfrom = datetime.strptime('2020-10-30', '%Y-%m-%d')
dto = datetime.strptime('2020-10-31', '%Y-%m-%d')

data = temperature.get(55.47, 37.32, dfrom, dto)
tm.sleep(1.5)
data = temperature.get(55.47, 37.32, dfrom, dto)

if isinstance(data, list):
    logging.disable(logging.DEBUG)
    fig, ax = plt.subplots()
    level = [a[1] for a in data]
    drange = [a[0] for a in data]
    ax.plot(drange, level, 'c')
    node_level = [data[i][1] for i in range(0, len(data), 6)]
    node_date = [data[i][0] for i in range(0, len(data), 6)]
    ax.plot(node_date, node_level, 'r.')
    legend = plt.legend(['temperature'])
    plt.setp(legend.get_texts(), color='grey')
    plt.show()

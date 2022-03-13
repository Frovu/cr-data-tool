import requests
import numpy as np
from datetime import datetime

url = 'http://cr0.izmiran.ru/scripts/nm64queryD.dll/mosc?'

def obtain(interval):
    a, b = [datetime.utcfromtimestamp(i) for i in interval]
    uri = f'{url}y1={a.year}&m1={a.month}&d1={a.day}&h1={a.hour}&y2={b.year}&m2={b.month}&d2={b.day}&h2={b.hour}&mn2=59&res=1_hour'
    res = requests.get(uri)
    result = []
    splitlines = res.text.splitlines()
    idx = splitlines.index('*'*57) + 1
    for line in splitlines[idx:]:
        if '*'*32 in line: break
        date, time, value = line.split()
        time = datetime.strptime(date+'T'+time, '%Y.%m.%dT%H:%M')
        value = float(value)/9600
        result.append((time, (value-1)*100 if value>0 else None))
    result = np.array(result)
    return result[:,0], result[:,1]

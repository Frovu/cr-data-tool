import os
import numpy as np
from datetime import datetime
SRC = 'tmp/Nagoya'
CHANNELS = 'V N S E W NE SE NW SW N2 S2 E2 W2 N3 S3 E3 W3'.split()

def parse(year):
    dir = f'{SRC}/{year}_nagoya/'
    all_files = sorted(os.listdir(dir))
    for month in range(1, 13):
        data = []
        files = [f for f in all_files if f.startswith(f'h{year}{month:02}')]
        for file in files:
            try:
                with open(dir+file) as f:
                    for line in f.readlines():
                        split = line.split()
                        date = datetime(*[int(i) for i in split[:4]])
                        data.append((date, *[int(i) for i in split[5:5+len(CHANNELS)]], float(split[39])))
            except:
                print(file + ' failed')
        data = np.array(data)
        dates = data[:,0]
        fname = f'{year%100:02}{month:02}.txt'
        print(f'{SRC}/?/{fname}')
        for i, c in enumerate(CHANNELS):
            counts = data[:,i+1] / 60
            with open(f'{SRC}/{c}/{fname}', 'w') as f:
                for date, count in np.column_stack((dates, counts)):
                    dt = datetime.strftime(date, '%Y-%m-%d %H:%M:%S+00')
                    f.write(f'{dt}{round(count,2):>12.2f}\n')

if __name__ == '__main__':
    parse(2017)
    parse(2018)
    parse(2019)

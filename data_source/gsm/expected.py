import data_source.gsm.result as gsm
import logging
import numpy as np

# C0, C10, A11, Ph11
GSM_COEF = dict({
    'Moscow': (0.7360, 0.0989, 0.5990, 58.20),
    'Nagoya': (0.6620, 0.1196, 0.4984, 53.30),
    'Apatity': (0.7900, 0.3950, 0.6220, 43.58),
    'Barentsburg': (0.7900, 0.3950, 0.6220, 43.58)
})

def get_variation(channel, interval, period=3600):
    a10, x, y, z = gsm.get(interval)
    time = np.arange(interval[0], interval[1]+1, period)
    if time.shape != a10.shape:
        return None, None
    # logging.debug(f'GSM: rotating planet')
    time_of_day = (time + period / 2) % 86400
    phi = 2 * np.pi * time_of_day / 86400 # planet rotation
    x = x * np.cos(phi)      + y * np.sin(phi)
    y = x * np.sin(phi) * -1 + y * np.cos(phi)
    # logging.debug(f'GSM: station coefs')
    c0, c10, a11, p11 = GSM_COEF[channel.station_name]
    lat, lon = channel.coordinates
    p11_station = ((lon + p11) % 360 / 360) * 2*np.pi
    Cx = -1 * a11 * np.cos(p11_station)
    Cy = -1 * a11 * np.sin(p11_station)
    Cz = -1 * c10
    # logging.debug(f'GSM: expected variation')
    v = a10 * c0 + (x * Cx + y * Cy + z * Cz)
    # logging.debug(f'GSM: done')
    return time, v

import data_source.gsm.result as gsm
import logging
import numpy as np

# C0, C10, A11, Ph11
# ^([\.\d-]+)\s+([\.\d-]+)\s+([\.\d-]+)\s+([\.\d-]+)\s+nagoya\.([a-zA-Z]+\d?)$  => ('Nagoya', '$5'): ($1, $2, $3, $4),
GSM_COEF = dict({
    ('Moscow-pioneer', 'V'): (0.7360, 0.0989, 0.5990, 58.20),
    ('Moscow-CARPET', 'V'): (0.7360, 0.0989, 0.5990, 58.20),
    ('Moscow-CUBE', 'V'): (0.7360, 0.0989, 0.5990, 58.20),
    ('Nagoya', 'V'): (0.6620, 0.1196, 0.4984, 53.30),
    ('Nagoya', 'N'): (0.6377, 0.1847, 0.4445, 69.60),
    ('Nagoya', 'S'): (0.6439, 0.0063, 0.5207, 42.20),
    ('Nagoya', 'E'): (0.6308, 0.0003, 0.4981, 71.80),
    ('Nagoya', 'W'): (0.6468, 0.2305, 0.4452, 35.00),
    ('Nagoya', 'NE'): (0.6057, 0.0613, 0.4629, 83.2),
    ('Nagoya', 'NW'): (0.6233, 0.2891, 0.3672, 54.8),
    ('Nagoya', 'SE'): (0.6139, -0.0846, 0.4901, 62.3),
    ('Nagoya', 'SW'): (0.6267, 0.1090, 0.4990, 23.4),
    ('Nagoya', 'N2'): (0.5480, 0.1722, 0.3541, 86.8),
    ('Nagoya', 'S2'): (0.5549, -0.0828, 0.4263, 35.9),
    ('Nagoya', 'E2'): (0.5332, -0.0897, 0.4078, 86.8),
    ('Nagoya', 'W2'): (0.5590, 0.2523, 0.3334, 17.8),
    ('Nagoya', 'N3'): (0.4641, 0.1387, 0.3164, 97.2),
    ('Nagoya', 'S3'): (0.4687, -0.1310, 0.3507, 31.9),
    ('Nagoya', 'E3'): (0.4445, -0.1205, 0.3272, 95.8),
    ('Nagoya', 'W3'): (0.4641, 0.1387, 0.3164, 97.2),
    ('Nagoya', 'G'): (0.0007, 0.3628, 0.2318, 177.5),
    ('Nagoya', 'GG'): (0.0078, 0.5171, 0.3323, 171.3),
    ('Apatity', 'V'): (0.7900, 0.3950, 0.6220, 43.58),
    ('Barentsburg', 'V'): (0.7900, 0.3950, 0.6220, 43.58)
})

def get_variation(channel, interval, period=3600):
    time = np.arange(interval[0], interval[1]+1, period)
    if (channel.station_name, channel.name) not in GSM_COEF:
        logging.warning(f'GSM: coef missing {channel.station_name}:{channel.name}')
        return time, np.full(time.shape, 0), np.full(time.shape, 0)
    gsm_result = gsm.get(interval)
    if not gsm_result or time.shape != gsm_result[0].shape:
        return None, None
    a10, x, y, z = gsm_result
    # logging.debug(f'GSM: rotating planet')
    time_of_day = (time + period / 2) % 86400
    phi = 2 * np.pi * time_of_day / 86400 # planet rotation
    x_station = x * np.cos(phi)      + y * np.sin(phi)
    y_station = x * np.sin(phi) * -1 + y * np.cos(phi)
    # logging.debug(f'GSM: station coefs')
    c0, c10, a11, p11 = GSM_COEF[(channel.station_name, channel.name)]
    lat, lon = channel.coordinates
    p11_station = ((lon + p11) % 360 / 360) * 2*np.pi
    Cx = -1 * a11 * np.cos(p11_station)
    Cy = -1 * a11 * np.sin(p11_station)
    Cz = -1 * c10
    isotropic = a10 * c0
    anisotropic = x_station * Cx + y_station * Cy + z * Cz
    return time, isotropic, anisotropic

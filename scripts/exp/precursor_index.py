import data_source.neutron.circles as circles
import data_source.neutron.database as database
from scipy import interpolate, signal, optimize
import numpy as np
import warnings
import matplotlib.pyplot as plt
from datetime import datetime, timezone
plt.rcParams['axes.facecolor'] = 'black'
plt.rcParams['figure.facecolor'] = 'darkgrey'

def _get(t_from, t_to, exclude=[]):
    stations = [k for k in circles.RING.keys() if k not in exclude]
    data, filtered, excluded = circles._filter(database.fetch((t_from, t_to), stations))
    print('filtered/excluded', filtered, excluded)
    base_idx = circles._determine_base(data)
    base_data = data[base_idx[0]:base_idx[1], 1:]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        variation = data[:,1:] / np.nanmean(base_data, axis=0) * 100 - 100
    return data[:,0], variation, np.array([circles._get_direction(s) for s in stations])

# index ignores actual asymptotic direction relative to the sun
def idx_polyfit(time, variations, directions, window: int = 3):
    sorted = np.argsort(directions)
    variations, directions = variations[:,sorted], directions[sorted]
    result = np.full((len(time), 4), np.nan, dtype=np.float32)
    dps = 360 / 86400
    for i in range(window, len(time)):
        x = np.concatenate([directions + time[i-t] * dps for t in range(window)]) % 360
        y = np.concatenate([variations[i-t] for t in range(window)])
        # print(x)
        # print(y)
        dist = (x[np.nanargmax(y)] + x[np.nanargmin(y)]) / 2
        x = (x + ((180 if dist < 180 else 360) - dist) + 360) % 360
        filter = np.isfinite(y)
        fit = np.polyfit(x[filter], y[filter], 3, full=True)
        residuals = fit[1][0]
        curve = np.poly1d(fit[0])
        roots = curve.deriv().roots

        roots = roots[np.where((roots < 360) & (roots > 0))]
        if len(roots) < 2: continue
        divergency = abs(curve(roots[0]) - curve(roots[1]))
        angle = 180 - abs(roots[0] - roots[1]) % 360
        idx = 100 * divergency / residuals * (angle / 180) ** 2
        # print(round(idx,2), angle, roots)
        result[i] = (idx, divergency, angle, residuals)
    return result

def plot():
    fig, ((axt1, ax1, ax2), (axt2, ax3, ax4)) = plt.subplots(2, 3, gridspec_kw={'width_ratios': [2, 1, 1], 'height_ratios': [1, 1]})
    colors = ['#00FFAA', '#00AAFF', '#ccFF00', '#50FF00']

    interval = [ datetime(2011, 2, 15), datetime(2011, 2, 21) ]
    interval = [ datetime(2022, 5, 10), datetime(2022, 5, 20) ]
    # interval = [ datetime(2021, 7, 4), datetime(2021, 7, 12) ]
    interval = [ t.replace(tzinfo=timezone.utc).timestamp() for t in interval ]
    time, variation, directions = _get(*interval)

    # p1_res = np.array([index_1(time[i], variation[i], directions) for i in range(0, len(time))])
    p1_res = index_windowed(time, variation, directions, 6)
    p1_res_w2 = index_windowed(time, variation, directions, 5)
    p1_idx, p1_div, p1_ang = p1_res[:,0], p1_res[:,1], p1_res[:,2]
    # print(p1_idx)
    axt1.plot(time[~np.isnan(p1_idx)], p1_idx[~np.isnan(p1_idx)], color='#ff10a0', label=f'precursor_idx')
    axt1.plot(time[~np.isnan(p1_res_w2[:,0])], p1_res_w2[:,0][~np.isnan(p1_res_w2[:,0])], color='#af10f0', label=f'precursor_idx')
    twx = axt1.twinx()
    twx.plot(time, variation, color='#00ffff')

    axt2.plot(time, p1_res[:,3], lw=2, color='#ff10a0', label=f'resid')
    axt2.plot(time, p1_div, lw=1.5, color='#00ffff', label=f'diff')
    twx = axt2.twinx()
    twx.plot(time, p1_ang, lw=2, color=colors[2], label=f'angle')

    # def plot_savgol(i, ax):
    #     nonlocal time, variation, directions
    #     rotated = (directions[~np.isnan(variation[i])] + time[i] / 86400 * 360) % 360
    #     sorted = np.argsort(rotated)
    #     sorted = sorted[~np.isnan(variations[sorted])]
    #     ax.plot(rotated, variations, 'ro', ms=6)


    def plot_idx(i, ax, window=3):
        nonlocal time, variation, directions
        sorted = np.argsort(directions)
        variations, directions = variation[:,sorted], directions[sorted]
        x = np.concatenate([directions + time[i-t] * 360 / 86400 for t in range(window)]) % 360
        y = np.concatenate([variations[i-t] for t in range(window)])
        filter = np.isfinite(y)
        x, y = x[filter], y[filter]
        amax, amin = x[np.argmax(y)], x[np.argmin(y)]
        approx_dist = np.abs(amax - amin)
        center_target = 180 if approx_dist < 180 else 360
        shift = center_target - (amax + amin) / 2
        x = (x + shift + 360) % 360
        curve = np.poly1d(np.polyfit(x, y, 3))
        roots = curve.deriv().roots

        # rotated = np.concatenate((rotated[sorted], rotated[sorted][:len(sorted)//3]+360))
        # variations = np.concatenate((variations, variations[:len(sorted)//3]))
        ax.plot(x, y, 'ro', ms=6)
        # ax.plot((x+180)%360, y, 'co', ms=6)
        # print(rotated)
        # print(variations)
        # # print(spline.derivative().roots())
        # # circle = spline(np.arange(0, 360, 1))
        rng = np.arange(30, 330, 1)
        angle = abs(roots[0] - roots[1]) % 360
        if angle > 180: angle = 360 - angle
        print('=', angle, '=', roots)
        ax.plot(rng, curve(rng), 'b', lw=3)
        # x, y = signal.savgol_filter((rotated, variations), 181, 3)
        # ax.plot(x, y, 'y', lw=3)
        def fn(x, a, scale, sx, sy):
            return np.cos(x * a * np.pi / 180 + sx) * scale + sy
        bb = ([-np.inf, -np.inf, -np.inf, -np.inf], [np.inf, np.inf, np.inf, np.inf])
        bounds = (approx_dist if approx_dist > 180 else (360-approx_dist)) / 4
        print(round(bounds), round(approx_dist), round(shift))
        trim = np.where((x > bounds) & (x < 360-bounds))
        popt, pcov = optimize.curve_fit(fn, x[trim], y[trim], bounds=bb)
        print('\\_/', popt)
        ax.plot(rng, fn(rng, *popt), 'c', lw=3)

        trim = np.where((x > 45) & (x < 360-45))
        popt, pcov = optimize.curve_fit(fn, x[trim], y[trim], bounds=bb)
        print('\\_/', popt)
        ax.plot(rng, fn(rng, *popt), 'y', lw=3)
        ax.set_title(f'i={np.round(p1_idx[i])} a={round(angle,1)}  {np.round(roots, 1)}')

    half = len(p1_idx)//2
    plot_idx(np.nanargmax(p1_idx)+1, ax1)
    plot_idx(np.nanargmin(p1_ang)+1, ax2)
    plot_idx(np.nanargmax(p1_idx[:half])+half+1, ax3)
    plot_idx(np.nanargmin(p1_ang)-2, ax4)

    legend = plt.legend()
    plt.setp(legend.get_texts(), color='grey')
    plt.show()

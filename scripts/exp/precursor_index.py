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

def idx_sinr(time, variations, directions, window: int = 3, min_scl = 1):
    sorted = np.argsort(directions)
    variations, directions = variations[:,sorted], directions[sorted]
    result = np.full((len(time), 4), np.nan, dtype=np.float32)
    def fn(x, a, scale, sx, sy):
        return np.cos(x * a * np.pi / 180 + sx) * scale + sy
    for i in range(window, len(time)):
        x = np.concatenate([directions + time[i-t] * 360 / 86400 for t in range(window)]) % 360
        y = np.concatenate([variations[i-t] for t in range(window)])
        filter = np.isfinite(y)
        x, y = x[filter], y[filter]
        # height = abs(np.max(y) - np.min(y))
        # y = y / height # rebase
        amax, amin = x[np.argmax(y)], x[np.argmin(y)]
        approx_dist = np.abs(amax - amin)
        center_target = 180 if approx_dist < 180 else 360
        shift = center_target - (amax + amin) / 2
        x = (x + shift + 360) % 360
        # bb = ([1, -np.inf, -np.inf, -np.inf], [2, np.inf, np.inf, np.inf])
        bounds = (approx_dist if approx_dist > 180 else (360-approx_dist)) / 6
        trim = np.where((x > bounds) & (x < 360-bounds))
        try:
            popt, pcov = optimize.curve_fit(fn, x[trim], y[trim])
            angle, scale = abs(popt[0]), abs(popt[1]) * 2
            dists  = np.array([fn(x[trim][j], *popt)-y[trim][j] for j in range(len(trim[0]))])
            mean_dist = (1.1 - np.mean(np.abs(dists)) / scale) ** 2

            if angle < 1 or angle > 2.5: angle = 0
            idx = (scale * angle ** 2 / 2 * mean_dist) if scale >= min_scl else 0
            result[i] = (idx, scale, angle, mean_dist)
        except:
            result[i] = (np.nan, np.nan, np.nan, np.nan)
    return result


def plot():
    fig, ((axt1, ax1, ax2), (axt2, ax3, ax4)) = plt.subplots(2, 3, gridspec_kw={'width_ratios': [2, 1, 1], 'height_ratios': [1, 1]})
    colors = ['#00FFAA', '#00AAFF', '#ccFF00', '#50FF00']

    # interval = [ datetime(2011, 2, 15), datetime(2011, 2, 19) ]
    interval = [ datetime(2022, 5, 16), datetime(2022, 5, 21) ]
    interval = [ datetime(2021, 10, 31), datetime(2021, 11, 4) ]
    # interval = [ datetime(2022, 6, 28), datetime(2022, 7, 3) ]
    # interval = [ datetime(2012, 7, 12), datetime(2012, 7, 16) ]
    interval = [ t.replace(tzinfo=timezone.utc).timestamp() for t in interval ]
    time, variation, directions = _get(*interval, ['KIEL2', 'NRLK'])
    dtime = np.array([datetime.utcfromtimestamp(t) for t in time])

    # p1_res = np.array([index_1(time[i], variation[i], directions) for i in range(0, len(time))])
    p1_res = idx_sinr(time, variation, directions, 2)
    # p1_res_w2 = idx_polyfit(time, variation, directions, 5)
    p1_res_w2 = idx_sinr(time, variation, directions, 3)
    p1_idx, p1_div, p1_ang = p1_res[:,0], p1_res[:,1], p1_res[:,2]
    # print(p1_idx)
    twx = axt1.twinx()
    twx.plot(dtime, variation, lw=1, color='#00ffff')
    axt1.plot(dtime[~np.isnan(p1_idx)], p1_idx[~np.isnan(p1_idx)], lw=3, color='#ff10a0', label=f'precursor_idx')
    axt1.plot(dtime[~np.isnan(p1_res_w2[:,0])], p1_res_w2[:,0][~np.isnan(p1_res_w2[:,0])], color='#af10f0', label=f'precursor_idx')

    axt2.plot(dtime, p1_res[:,3], lw=2, color='#ff10a0', label=f'resid')
    axt2.plot(dtime[p1_ang>0], p1_div[p1_ang>0], lw=1.5, color='#00ffff', label=f'diff')
    twx = axt2.twinx()
    twx.plot(dtime[p1_ang>0], p1_ang[p1_ang>0], lw=2, color=colors[2], label=f'a')

    # def plot_savgol(i, ax):
    #     nonlocal time, variation, directions
    #     rotated = (directions[~np.isnan(variation[i])] + time[i] / 86400 * 360) % 360
    #     sorted = np.argsort(rotated)
    #     sorted = sorted[~np.isnan(variations[sorted])]
    #     ax.plot(rotated, variations, 'ro', ms=6)


    def plot_idx(i, ax, window=2):
        nonlocal time, variation, directions
        sorted = np.argsort(directions)
        variations, direction = variation[:,sorted], directions[sorted]
        x = np.concatenate([direction + time[i-t] * 360 / 86400 for t in range(window)]) % 360
        y = np.concatenate([variations[i-t] for t in range(window)])
        filter = np.isfinite(y)
        x, y = x[filter], y[filter]
        # dist = abs(np.max(y) - np.min(y))
        # y = y / dist # rebase
        amax, amin = x[np.argmax(y)], x[np.argmin(y)]
        approx_dist = np.abs(amax - amin)
        center_target = 180 if approx_dist < 180 else 360
        shift = center_target - (amax + amin) / 2
        x = (x + shift + 360) % 360

        ax.plot(x, y, 'ro', ms=6)
        rng = np.arange(30, 330, 1)
        # # circle = spline(np.arange(0, 360, 1))
        # curve = np.poly1d(np.polyfit(x, y, 3))
        # roots = curve.deriv().roots
        # angle = abs(roots[0] - roots[1]) % 360
        # if angle > 180: angle = 360 - angle
        # print('=', angle, '=', roots)
        # ax.plot(rng, curve(rng), 'b', lw=3)
        # x, y = signal.savgol_filter((rotated, variations), 181, 3)
        # ax.plot(x, y, 'y', lw=3)
        def fn(x, a, scale, sx, sy):
            return np.cos(x * a * np.pi / 180 + sx) * scale + sy
        bb = ([-np.inf, -np.inf, -np.inf, -np.inf], [np.inf, np.inf, np.inf, np.inf])
        bounds = (approx_dist if approx_dist > 180 else (360-approx_dist)) / 8
        print(round(bounds), round(approx_dist), round(shift))
        trim = np.where((x > bounds) & (x < 360-bounds))
        try:
            popt, pcov = optimize.curve_fit(fn, x[trim], y[trim], bounds=bb)

            dist = np.array([fn(x[trim][j], *popt)-y[trim][j] for j in range(len(trim[0]))])
            print(np.mean(np.abs(dist)), np.var(y))
            print('\\_/', popt)
            ax.plot(rng, fn(rng, *popt), 'c', lw=3)
            ax.set_title(f'{dtime[i]} i={p1_idx[i]:.2f} a={p1_ang[i]:.2f} s={p1_div[i]:.2f} {p1_res[:,3][i]:.2f}')

            # def fn(x, a, b, scale, sx, sy):
            #     return np.sin(x * a * np.pi / 180 + sx) * scale + np.sin(x * b * np.pi / 180 + sx) * scale + sy
            # # trim = np.where((x > 30) & (x < 360-30))
            # popt, pcov = optimize.curve_fit(fn, x[trim], y[trim])
            # print('\\_/\\_', popt)
            # ax.plot(rng, fn(rng, *popt), 'y', lw=3)


        except:
            print('failed')

    half = len(p1_idx)//2
    plot_idx(np.nanargmax(p1_idx[:half]), ax1)
    plot_idx(np.nanargmax(p1_idx[half:])+half, ax2)
    plot_idx(np.nanargmax(p1_idx[half:])+half+1, ax3)
    # plot_idx(np.nanargmax(p1_ang), ax2)
    # plot_idx(np.nanargmax(p1_ang[:half]), ax3)
    plot_idx(np.nanargmax(p1_ang[half:])+half, ax4)
    # plot_idx(np.nanargmax(p1_res[:,3][half:])+half, ax4)

    legend = plt.legend()
    plt.setp(legend.get_texts(), color='grey')
    plt.show()

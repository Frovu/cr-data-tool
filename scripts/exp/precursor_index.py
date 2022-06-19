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

def index_bad1(time, variations, directions, angular_precision = 1):
    rotated = (directions[~np.isnan(variations)] + time / 86400 * 360) % 360
    sorted = np.argsort(rotated)
    sorted = sorted[~np.isnan(variations[sorted])]
    spline = interpolate.UnivariateSpline(rotated[sorted], variations[sorted], k=4)
    roots = spline.derivative().roots()

    # if len(roots) != 2: return 0, 0, 180
    if len(roots) < 2: return np.nan, np.nan, np.nan
    circle = spline(np.arange(0, 360, angular_precision))
    # min_i, max_i = [int(round(r, angular_precision)) for r in roots]
    i_roots = [int(round(r, angular_precision)) for r in roots]
    min_i, max_i = i_roots[np.argmin(circle[i_roots])], i_roots[np.argmax(circle[i_roots])]
    divergency = circle[max_i] - circle[min_i]
    angle = abs(min_i - max_i) * angular_precision
    if angle > 180: angle = 360 - angle
    idx = divergency * (180 / angle) ** 2 if angle > 0 else -1
    # if divergency >= 1: return 0
    return idx, divergency, angle

def index_1(time, variations, directions):
    rotated = (directions[~np.isnan(variations)] + time / 86400 * 360) % 360
    sorted = np.argsort(rotated)
    sorted = sorted[~np.isnan(variations[sorted])]
    curve = np.poly1d(np.polyfit(rotated[sorted], variations[sorted], 3))
    roots = curve.deriv().roots
    roots = roots[np.where((roots < 360) & (roots > 0))]
    if len(roots) < 2: return np.nan, np.nan, np.nan
    divergency = abs(curve(roots[0]) - curve(roots[1]))
    angle = abs(roots[0] - roots[1]) % 180
    if angle > 90: angle = 180 - angle
    # idx = divergency * angle
    idx = divergency * (180 / angle) ** 2 if angle > 0 else -1
    # if divergency >= 1: return 0
    return idx, divergency, angle

def plot():
    fig, ((axt1, ax1, ax2), (axt2, ax3, ax4)) = plt.subplots(2, 3, gridspec_kw={'width_ratios': [2, 1, 1], 'height_ratios': [1, 1]})
    colors = ['#00FFAA', '#00AAFF', '#ccFF00', '#50FF00']

    interval = [ datetime(2011, 2, 15), datetime(2011, 2, 21) ]
    interval = [ datetime(2022, 5, 13), datetime(2022, 5, 22) ]
    interval = [ t.replace(tzinfo=timezone.utc).timestamp() for t in interval ]
    time, variation, directions = _get(*interval)

    p1_res = np.array([index_1(time[i], variation[i], directions) for i in range(0, len(time))])
    p1_idx, p1_div, p1_ang = p1_res[:,0], p1_res[:,1], p1_res[:,2]
    # print(p1_idx)
    axt1.plot(time, variation, color='#00ffff')
    twx = axt1.twinx()
    twx.plot(time, p1_idx, color='#ff10a0', label=f'precursor_idx')

    axt2.plot(time, p1_div, lw=1.5, color='#00ffff', label=f'diff')
    twx = axt2.twinx()
    twx.plot(time, p1_ang, lw=2, color=colors[2], label=f'angle')

    # def plot_savgol(i, ax):
    #     nonlocal time, variation, directions
    #     rotated = (directions[~np.isnan(variation[i])] + time[i] / 86400 * 360) % 360
    #     sorted = np.argsort(rotated)
    #     sorted = sorted[~np.isnan(variations[sorted])]
    #     ax.plot(rotated, variations, 'ro', ms=6)


    def plot_idx(i, ax):
        nonlocal time, variation, directions
        print(time[i], p1_ang[i], p1_idx[i])
        variations = variation[i]
        rotated = (directions[~np.isnan(variations)] + time[i] / 86400 * 360) % 360
        variations = np.concatenate((variation[i], variation[i+1], variation[i+2]))
        rotated = np.concatenate(( \
            (directions[~np.isnan(variation[i])] + time[i] / 86400 * 360) % 360, \
            (directions[~np.isnan(variation[i])] + time[i+1] / 86400 * 360) % 360, \
            (directions[~np.isnan(variation[i])] + time[i+2] / 86400 * 360) % 360))
        sorted = np.argsort(rotated)
        variations = variations[~np.isnan(variations)][sorted]
        rotated = np.roll(rotated[sorted], 0)
        variations = np.roll(variations, 0)
        # rotated = np.concatenate((rotated[sorted], rotated[sorted][:len(sorted)//3]+360))
        # variations = np.concatenate((variations, variations[:len(sorted)//3]))
        ax.plot(rotated, variations, 'ro', ms=6)
        # print(rotated)
        # print(variations)
        # # print(spline.derivative().roots())
        # # circle = spline(np.arange(0, 360, 1))
        rng = np.arange(0, 360, 1)
        cc = np.polyfit(rotated, variations, 3)
        roots = np.poly1d(np.polyfit(rotated, variations, 3)).deriv().roots
        angle = abs(roots[0] - roots[1]) % 180
        if angle > 90: angle = 180 - angle
        print('=', angle, '=', roots)
        ax.plot(rng, np.poly1d(cc)(rng), 'b', lw=3)
        # x, y = signal.savgol_filter((rotated, variations), 181, 3)
        # ax.plot(x, y, 'y', lw=3)
        def fn(x, a, b, d):
            return np.cos(x * a * np.pi / 180 + b) + d
        popt, pcov = optimize.curve_fit(fn, rotated, variations)
        print('\\_/', popt)
        ax.plot(rng, fn(rng, *popt), 'y', lw=3)

        # def fn2(x, a, b, c, v):
        #     return (a*x**3 + b*x**2 + c*x) + v
        # popt, pcov = optimize.curve_fit(fn2, rotated, variations)
        # print('\\_/', popt)
        # ax.plot(rng, fn2(rng, *popt), 'b', lw=3)


        # print(spline.derivative().get_knots())
        # print(spline.derivative().get_coeffs())
        # print('roots', np.roots(spline.derivative().get_coeffs()))
        # ax.plot(rng, spline.derivative()(rng), 'y', lw=3)
        # print(np.argmin(np.abs(spline.derivative()(np.arange(0, 360, 1)))))
        # print(np.argmin(np.abs(spline.derivative()(np.arange(0, 360, 1)))))
        # roots = spline.derivative().roots()
        # i_roots = [int(round(r, 1)) for r in roots]
        # min_i, max_i = i_roots[np.argmin(circle[i_roots])], i_roots[np.argmax(circle[i_roots])]
        # divergency = circle[max_i] - circle[min_i]
        # angle = abs(min_i - max_i) * 1
        # if angle > 180: angle = 360 - angle
        # print(min_i, max_i, angle)
        # idx = divergency * (180 / angle) ** 2 if angle > 0 else 0
        # spline.set_smoothing_factor(2)
        # ax.plot(np.arange(0, 360, 1), spline(np.arange(0, 360, 1)), 'g', lw=3)

    half = len(p1_idx)//2
    plot_idx(np.nanargmax(p1_idx)+0, ax1)
    plot_idx(np.nanargmax(p1_ang), ax2)
    plot_idx(np.nanargmax(p1_idx)+1, ax3)
    plot_idx(np.nanargmin(p1_ang), ax4)

    legend = plt.legend()
    plt.setp(legend.get_texts(), color='grey')
    plt.show()

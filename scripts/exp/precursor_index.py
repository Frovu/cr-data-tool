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
    return idx, divergency, angle, np.std

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

# index ignores actual asymptotic direction relative to the sun
def index_windowed(time, variations, directions, window: int = 4):
    sorted = np.argsort(directions)
    variations, directions = variations[:,sorted], directions[sorted]
    result = np.full((len(time), 4), np.nan, dtype=np.float32)
    dps = 360 / 86400
    for i in range(window, len(time)):
        x = np.concatenate([directions + time[i-t] * dps for t in range(window)]) % 360
        y = np.concatenate([variations[i-t] for t in range(window)])
        # print(x)
        # print(y)
        dist = (x[np.argmax(y)] + x[np.argmin(y)]) / 2
        x = (x + ((180 if dist < 180 else 180) - dist) + 360) % 360
        filter = np.isfinite(y)
        fit = np.polyfit(x[filter], y[filter], 3, full=True)
        residuals = fit[1][0]
        curve = np.poly1d(fit[0])
        roots = curve.deriv().roots

        roots = roots[np.where((roots < 360) & (roots > 0))]
        if len(roots) < 2: continue
        divergency = abs(curve(roots[0]) - curve(roots[1]))
        angle = 180 - abs(roots[0] - roots[1]) % 360
        idx = 10 * divergency / residuals * (angle / 180) ** 2
        # print(round(idx,2), angle, roots)
        result[i] = (idx, divergency, angle, residuals)
    return result

def plot():
    fig, ((axt1, ax1, ax2), (axt2, ax3, ax4)) = plt.subplots(2, 3, gridspec_kw={'width_ratios': [2, 1, 1], 'height_ratios': [1, 1]})
    colors = ['#00FFAA', '#00AAFF', '#ccFF00', '#50FF00']

    interval = [ datetime(2011, 2, 15), datetime(2011, 2, 21) ]
    interval = [ datetime(2022, 5, 13), datetime(2022, 5, 22) ]
    interval = [ t.replace(tzinfo=timezone.utc).timestamp() for t in interval ]
    time, variation, directions = _get(*interval)

    # p1_res = np.array([index_1(time[i], variation[i], directions) for i in range(0, len(time))])
    p1_res = index_windowed(time, variation, directions)
    p1_idx, p1_div, p1_ang = p1_res[:,0], p1_res[:,1], p1_res[:,2]
    # print(p1_idx)
    axt1.plot(time, variation, color='#00ffff')
    twx = axt1.twinx()
    twx.plot(time, p1_idx, color='#ff10a0', label=f'precursor_idx')

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


    def plot_idx(i, ax, window=4):
        nonlocal time, variation, directions
        sorted = np.argsort(directions)
        variations, directions = variation[:,sorted], directions[sorted]
        x = np.concatenate([directions + time[i-t] * 360 / 86400 for t in range(window)]) % 360
        y = np.concatenate([variations[i-t] for t in range(window)])
        # print(x)
        # print(y)

        dist = (x[np.argmax(y)] + x[np.argmin(y)]) / 2
        print('d', dist)
        x = (x + ((180 if dist < 180 else 360) - dist) + 360) % 360
        # x = (x + (180 - (x[np.argmax(y)] + x[np.argmin(y)]) / 2) + 360) % 360
        filter = np.isfinite(y)
        curve = np.poly1d(np.polyfit(x[filter], y[filter], 3))
        roots = curve.deriv().roots

        # rotated = np.concatenate((rotated[sorted], rotated[sorted][:len(sorted)//3]+360))
        # variations = np.concatenate((variations, variations[:len(sorted)//3]))
        ax.plot(x, y, 'ro', ms=6)
        ax.plot((x+180)%360, y, 'co', ms=6)
        # print(rotated)
        # print(variations)
        # # print(spline.derivative().roots())
        # # circle = spline(np.arange(0, 360, 1))
        rng = np.arange(0, 360, 1)
        angle = abs(roots[0] - roots[1]) % 360
        if angle > 180: angle = 360 - angle
        print('=', angle, '=', roots)
        ax.plot(rng, curve(rng), 'b', lw=3)
        # x, y = signal.savgol_filter((rotated, variations), 181, 3)
        # ax.plot(x, y, 'y', lw=3)
        def fn(x, a, b, d):
            return np.cos(x * a * np.pi / 180 + b) + d
        popt, pcov = optimize.curve_fit(fn, x[filter], y[filter])
        print('\\_/', popt)
        ax.plot(rng, fn(rng, *popt), 'y', lw=3)
        ax.set_title(f'i={np.round(p1_idx[i])} a={round(angle,1)}  {np.round(roots, 1)}')
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
    plot_idx(np.nanargmin(p1_ang), ax2)
    plot_idx(np.nanargmax(p1_idx[:half])+half, ax3)
    plot_idx(np.nanargmin(p1_ang)-2, ax4)

    legend = plt.legend()
    plt.setp(legend.get_texts(), color='grey')
    plt.show()

import uPlot from './uPlot.iife.min.js';

const MIN_HEIGHT = 360;
let uplot;
const parentEl = document.getElementsByClassName('graph')[0];

function getPlotSize() {
	const height = parentEl.offsetWidth * 0.5;
	return {
		width: parentEl.offsetWidth,
		height: height > MIN_HEIGHT ? height : MIN_HEIGHT,
	};
}

function prepareSeries(series) {
	return series.map(s => {
		return s === 'time' ? { value: '{YYYY}-{MM}-{DD} {HH}:{mm}' } : {
			stroke: s.color,
			label: s.label,
			scale: s.scale,
			value: (u, v) => v == null ? '-' : v.toFixed(s.precision||0) + ' ' + s.scale,
		};
	});
}

function prepareAxes(axes) {
	return axes.map(a => {
		return a === 'time' ? {} : {
			scale: a.scale,
			values: (u, vals) => vals.map(v => v.toFixed(a.precision||0) + ' ' + a.scale),
		};
	});
}

export function init(series, axes) {
	if (uplot) uplot.destroy();
	uplot = new uPlot({
		...getPlotSize(),
		series: prepareSeries(series),
		axes: prepareAxes(axes),
		cursor: {
			drag: { dist: 12 },
			points: { size: 6, fill: (self, i) => self.series[i]._stroke }
		}
	}, null, parentEl);
	window.addEventListener('resize', () => {
		uplot.setSize(getPlotSize());
	});
}

export function data(data) {
	if (uplot)
		uplot.setData(data);
	else
		console.error('plot does not exist');
}

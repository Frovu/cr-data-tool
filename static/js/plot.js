import uPlot from './uPlot.iife.min.js';

const MIN_HEIGHT = 360;
let uplot;
let plotTime;
const parentEl = document.getElementsByClassName('graph')[0];
window.addEventListener('resize', () => {
	if (uplot) uplot.setSize(getPlotSize());
});

function getPlotSize() {
	const height = parentEl.offsetWidth * (plotTime?0.5:0.75);
	return {
		width: parentEl.offsetWidth,
		height: height > (window.innerHeight-80) ? window.innerHeight-80 : (height > MIN_HEIGHT ? height : MIN_HEIGHT),
	};
}

function prepareSeries(series) {
	return series.map(s => {
		return {
			stroke: s.color,
			label: s.label,
			scale: s.scale,
			value: (u, v) => v == null ? '-' : (s.transform?s.transform(v):v).toFixed(s.precision||0) + ' ' + s.scale,
		};
	});
}

function prepareAxes(axes) {
	return axes.map(a => {
		return Object.assign(a, {
			values: (u, vals) => vals.map(v => (a.transform?a.transform(v):v).toFixed(a.precision||0) + ' ' + a.scale)
		});
	});
}

export function init(axes, time=true, scales, series) {
	plotTime = time;
	if (uplot) uplot.destroy();
	uplot = new uPlot({
		...getPlotSize(),
		tzDate: ts => uPlot.tzDate(new Date(ts * 1e3), 'UTC'),
		series: time?[{ value: '{YYYY}-{MM}-{DD} {HH}:{mm} UTC' }]:
			(series?prepareSeries(series):[]),
		axes: (time?[{}]:[]).concat(prepareAxes(axes)),
		scales,
		cursor: {
			drag: { dist: 12 },
			points: { size: 6, fill: (self, i) => self.series[i]._stroke }
		}
	}, null, parentEl);
	// uplot = new uPlot({
	// 	...getPlotSize(),
	// 	// tzDate: ts => uPlot.tzDate(new Date(ts * 1e3), 'UTC'),
	// 	// series: [{label: 'x', sorted: 1}, {label: 'y', stroke: 'red'}],
	// 	series: prepareSeries(series),
	// 	axes: [
	// 		{ scale: 'mb', side: 3},
	// 		{ scale: 'K', side: 2}
	// 	],
	// 	scales: {
	// 		mb: {
	// 			time: false,
	// 			dir: -1,
	// 			ori: 1
	// 		},
	// 		K: {
	// 			dir: 1,
	// 			ori: 0
	// 		}
	// 	},
	// 	// scales: {x: {time: false, ori: 1}},
	// 	cursor: {
	// 		drag: { dist: 12 },
	// 		points: { size: 6, fill: (self, i) => self.series[i]._stroke }
	// 	}
	// }, [
	// 	[1,2,3,4,5,6,7,8],
	// 	[4,2,3,5,6,7,10,9]
	// ], parentEl);
}

export function data(data, reset=true) {
	if (!uplot)
		return console.error('plot does not exist');
	uplot.setData(data, reset);
	if (!reset) uplot.redraw();
}

export function series(series) {
	const prepared = prepareSeries(series);
	const toDelete = uplot.series.length - (plotTime?1:0);
	for (let i=0; i < toDelete; ++i)
		uplot.delSeries(plotTime?1:0);
	for (let i=0; i < prepared.length; ++i)
		uplot.addSeries(prepared[i]);
	/*
	*** This code may be faster or more generic but is much less clean ***
	let found = [];
	for (let i=0; i < uplot.series.length; ++i) {
		const s = uplot.series[i];
		if (s.label === 'Time') {
			found.push(series.indexOf('time'));
			continue;
		}
		const idx = prepared.findIndex(es => es.label === s.label && s._stroke === es.stroke && s.scale === es.scale);
		if (idx >= 0)
			found.push(idx);
		else
			uplot.delSeries(i--);
	}
	prepared.forEach((s, i) => {
		if (!found.includes(i)) {
			found.push(i);
			found = found.sort((a, b) => a-b);
			uplot.addSeries(s, found.indexOf(i));
		}
	});
	*/
}

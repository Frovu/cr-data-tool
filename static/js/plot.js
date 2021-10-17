import uPlot from './uPlot.esm.js';

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
		return Object.assign(s, {
			stroke: s.color,
			paths: s.paths && uPlot.paths[s.paths](),
			value: (u, v) => v == null ? '-' : (s.transform?s.transform(v):v).toFixed(s.precision||0) + (s.nounit ? '' : ' '+s.scale),
		});
	});
}

function prepareAxes(axes) {
	return axes.map(a => {
		return Object.assign(a, {
			values: (u, vals) => vals.map(v => (a.transform?a.transform(v):v).toFixed(a.precision||0) + (a.nounit ? '' : ' '+a.scale))
		});
	});
}

function linePaths() {
	return (u, seriesIdx) => {
		uPlot.orient(u, seriesIdx, (series, dataX, dataY, scaleX, scaleY, valToPosX, valToPosY, xOff, yOff, xDim, yDim) => {
			let d = u.data[seriesIdx];
			const ss = u.ctx.strokeStyle;
			u.ctx.strokeStyle = series.stroke();
			let p = new Path2D();
			for (let i = 0; i < d[0].length; i++) {
				let xVal = d[0][i];
				let yVal = d[1][i];
				if (xVal >= scaleX.min && xVal <= scaleX.max && yVal >= scaleY.min && yVal <= scaleY.max) {
					let cx = valToPosX(xVal, scaleX, xDim, xOff);
					let cy = valToPosY(yVal, scaleY, yDim, yOff);
					p.lineTo(cx, cy);
				}
			}
			u.ctx.stroke(p);
			u.ctx.strokeStyle = ss;
		});
	};
}

// ref: https://leeoniya.github.io/uPlot/demos/scatter.html
export function initCorr(data, label, pointPx, corrLine=false) {
	if (uplot) uplot.destroy();
	function drawPoints(u, seriesIdx) {
		const size = pointPx * devicePixelRatio;
		uPlot.orient(u, seriesIdx, (series, dataX, dataY, scaleX, scaleY, valToPosX, valToPosY, xOff, yOff, xDim, yDim, moveTo, lineTo, rect, arc) => {
			let d = u.data[seriesIdx];
			u.ctx.fillStyle = series.stroke();
			let deg360 = 2 * Math.PI;
			console.time('points');
			let p = new Path2D();
			for (let i = 0; i < d[0].length; i++) {
				let xVal = d[0][i];
				let yVal = d[1][i];
				if (xVal >= scaleX.min && xVal <= scaleX.max && yVal >= scaleY.min && yVal <= scaleY.max) {
					let cx = valToPosX(xVal, scaleX, xDim, xOff);
					let cy = valToPosY(yVal, scaleY, yDim, yOff);
					p.moveTo(cx + size/2, cy);
					arc(p, cx, cy, size/2, 0, deg360);
				}
			}
			console.timeEnd('points');
			u.ctx.fill(p);
		});
	}
	uplot = new uPlot({
		...getPlotSize(),
		mode: 2,
		legend: {
			live: false,
		},
		hooks: {
			drawClear: [
				u => {
					u.series.forEach((s, i) => {
						if (i > 0)
							s._paths = null;
					});
				},
			],
		},
		scales: {
			x: {
				time: false,
				range: (u, min, max) => [min, max],
			},
			y: {
				range: (u, min, max) => [min, max],
			},
		},
		cursor: {
			drag: { dist: 12 },
			points: { size: 6, fill: (self, i) => self.series[i]._stroke }
		},
		series: [
			{},
			{
				label: label,
				stroke: 'red',
				fill: 'rgba(255,0,0,0.1)',
				paths: drawPoints
			}
		].concat(!corrLine ? [] : [{
			label: 'r',
			stroke: 'rgba(155,0,255,0.8)',
			paths: linePaths()
		}])
	}, data, parentEl);
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
}

export function data(data, reset=true) {
	if (!uplot)
		return console.error('plot does not exist');
	uplot.setData(data, reset);
	if (!reset) uplot.redraw();
	console.log(uplot.data, uplot.series);
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

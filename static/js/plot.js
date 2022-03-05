import uPlot from './uPlot.esm.js';

const MIN_HEIGHT = 360;
let style = {};
let uplot;
let plotTime;
const parentEl = document.getElementsByClassName('graph')[0];
window.addEventListener('resize', () => {
	if (uplot) uplot.setSize(getPlotSize());
});

function getStyle() {
	const css = window.getComputedStyle(document.body);
	style = {
		font: css.font,
		grid: css.getPropertyValue('--color-grid'),
		text: css.getPropertyValue('--color-inactive'),
		bg: css.getPropertyValue('--color-tab-bg')
	};
}

function getPlotSize() {
	const height = Math.floor(parentEl.offsetWidth * (plotTime?0.5:0.75));
	return {
		width: parentEl.offsetWidth - 4,
		height: height > (window.innerHeight-80) ? window.innerHeight-80 : (height > MIN_HEIGHT ? height : MIN_HEIGHT),
	};
}

function prepareSeries(series) {
	return series.map(s => {
		return Object.assign(s, {
			fill: '#0000',
			stroke: s.color,
			paths: s.paths && uPlot.paths[s.paths](),
			points: { fill: style.bg, stroke: s.color },
			value: (u, v) => v == null ? '-' : (s.transform?s.transform(v):v).toFixed(s.precision||0) + (s.nounit ? '' : ' '+s.scale),
		});
	});
}

function prepareAxes(axes) {
	return axes.map(a => {
		return Object.assign(a, {
			font: style.font.replace('14px', '12px'),
			stroke: style.text,
			ticks: { stroke: style.grid, width: 1 },
			grid: { stroke: style.grid, width: 1 },
			values: (u, vals) => vals.map(v => (a.transform?a.transform(v):v).toFixed(a.precision||0) + (a.nounit ? '' : ''+a.scale))
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
export function initCorr(data, label, pointPx, title, corrLine=false) {
	if (uplot) uplot.destroy();
	getStyle();
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
	const axis = (scale, size) => { return {
		scale, size,
		font: style.font,
		stroke: style.text,
		values: (u, vals) => vals.map(v => v.toFixed(0) + (scale == 'y' ? '%' : '')),
		ticks: { stroke: style.grid, width: 1 },
		grid: { stroke: style.grid, width: 1 }
	}; };
	uplot = new uPlot({
		...getPlotSize(),
		title,
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
				range: [-10, 10],
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
				stroke: 'rgba(250,10,80,1)',
				fill: 'rgba(255,0,0,0.1)',
				paths: drawPoints
			}
		].concat(!corrLine ? [] : [{
			label: corrLine,
			stroke: 'rgba(100,0,200,1)',
			paths: linePaths()
		}]),
		axes: [ axis('x', 36), axis('y', 60) ]
	}, data, parentEl);
}

export function init(axes, time=true, scales, series, title) {
	getStyle();
	plotTime = time;
	if (uplot) uplot.destroy();
	uplot = new uPlot({
		...getPlotSize(),
		title,
		tzDate: ts => uPlot.tzDate(new Date(ts * 1e3), 'UTC'),
		series: time?[{ value: '{YYYY}-{MM}-{DD} {HH}:{mm} UTC', stroke: style.text }]:
			(series?prepareSeries(series):[]),
		axes: (time?[{
			font: style.font,
			grid: { stroke: style.grid, width: 1 }, stroke: style.text
		}]:[]).concat(prepareAxes(axes, style)),
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
}

export function series(series) {
	const prepared = prepareSeries(series);
	const toDelete = uplot.series.length - (plotTime?1:0);
	for (let i=0; i < toDelete; ++i)
		uplot.delSeries(plotTime?1:0);
	for (let i=0; i < prepared.length; ++i)
		uplot.addSeries(prepared[i]);
}

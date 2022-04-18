import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';
import uPlot from '../uPlot.esm.js';

const URL = 'api/neutron/circles';
const params = util.storage.getObject('circles-params') || {
	from: new Date(2021, 10, 1).getTime() / 1000,
	to: new Date(2021, 11, 15).getTime() / 1000,
};
let xdata = [], ydata = [], circles = [];
let stations = [];

function receiveData(resp) {
	const slen = resp.shift.length, tlen = resp.time.length;
	stations = resp.stations;
	xdata = Array(slen*tlen), ydata = Array(slen*tlen), circles = Array(slen*tlen);
	let maxVar = 0;
	for (let ti = 0; ti < tlen; ++ti) {
		for (let si = 0; si < slen; ++si) {
			const idx = ti*slen + si;
			const time = resp.time[ti], vv = resp.variation[ti][si];
			if (vv < maxVar) maxVar = vv;
			xdata[idx] = time;
			ydata[idx] = (time / 86400 * 360 + resp.shift[si]) % 360 - 180;
			circles[idx] = vv;
		}
	}
	circles = circles.map(c => Math.abs(c / maxVar) * 30 + 1);
	plotInit();
}

function drawPoints(u, seriesIdx) {
	uPlot.orient(u, seriesIdx, (series, dataX, dataY, scaleX, scaleY, valToPosX, valToPosY, xOff, yOff, xDim, yDim, moveTo, lineTo, rect, arc) => {
		let d = u.data[seriesIdx];
		u.ctx.fillStyle = series.stroke();
		let deg360 = 2 * Math.PI;
		let p = new Path2D();
		for (let i = 0; i < d[0].length; i++) {
			let size = circles[i] * devicePixelRatio;
			let xVal = d[0][i];
			let yVal = d[1][i];
			if (xVal >= scaleX.min && xVal <= scaleX.max && yVal >= scaleY.min && yVal <= scaleY.max) {
				let cx = valToPosX(xVal, scaleX, xDim, xOff);
				let cy = valToPosY(yVal, scaleY, yDim, yOff);
				p.moveTo(cx + size/2, cy);
				arc(p, cx, cy, size/2, 0, deg360);
			}
		}
		u.ctx.fill(p);
	});
}

function plotInit() {
	if (!xdata.length) return;
	console.log(plot.initCustom(style => {
		return {
			...plot.getPlotSize(true),
			mode: 2,
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
			axes: [
				{
					font: style.font,
					stroke: style.text,
					grid: { stroke: style.grid, width: 1 },
				},
				{
					label: 'longitude',
					scale: 'y',
					font: style.font,
					stroke: style.text,
					values: (u, vals) => vals.map(v => v.toFixed(0)),
					ticks: { stroke: style.grid, width: 1 },
					grid: { stroke: style.grid, width: 1 }
				}
			],
			scales: {
				x: {
					time: false,
					range: (u, min, max) => [min, max],
				},
				y: {
					range: [-185, 185],
				},
			},
			series: [
				{},
				{
					facets: [ { scale: 'x', auto: true }, { scale: 'y', auto: true } ],
					stroke: 'rgba(250,10,80,1)',
					fill: 'rgba(255,0,0,0.1)',
					paths: drawPoints
				}
			]
		};
	}, [ null, [xdata, ydata] ]));
}

const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('circles-params', p)
});

export function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Plot GLE precursors using stations ring method.`)
	]);
	tabs.fill('query', [
		tabs.input('time', (from, to, force) => {
			params.from = from;
			params.to = to;
			query.params(params);
			if (force)
				query.fetch(params);
		}, { from: params.from, to: params.to }),
		query.el
	]);
	query.fetch(params);
}

export function load() {
	plotInit();
}

export function unload() {
	if (query)
		query.stop();
}

import * as tabs from '../lib/tabsUtil.js';
import * as util from '../lib/util.js';
import * as plot from '../plot.js';
import uPlot from '../lib/uPlot.esm.js';

const URL = 'api/neutron/circles';
const params = util.storage.getObject('circles-params') || {
	from: new Date(2021, 10, 1).getTime() / 1000,
	to: new Date(2021, 11, 15).getTime() / 1000,
};
let pdata = [], ndata = [];
let stations = [], shifts = [];

function receiveData(resp) {
	const slen = resp.shift.length, tlen = resp.time.length;
	if (tlen < 10) return;
	stations = resp.stations, shifts = resp.shift;
	const data = Array.from(Array(4), () => new Array(slen*tlen));
	let maxVar = 0, posCount = 0;
	console.time('restructure');
	for (let ti = 0; ti < tlen; ++ti) {
		for (let si = 0; si < slen; ++si) {
			const idx = ti*slen + si;
			const time = resp.time[ti], vv = resp.variation[ti][si];
			if (vv < maxVar) maxVar = vv;
			if (vv >= 0) ++posCount;
			data[0][idx] = time;
			data[1][idx] = (time / 86400 * 360 + resp.shift[si]) % 360 - 180;
			data[2][idx] = vv;
			data[3][idx] = si;
		}
	}
	maxVar = Math.abs(maxVar);
	ndata = Array.from(Array(4), () => new Array(slen*tlen - posCount));
	pdata = Array.from(Array(4), () => new Array(posCount));
	console.log(maxVar);
	let pi = 0, ni = 0, len = slen*tlen;
	for (let idx = 0; idx < len; ++idx) {
		const vv = data[2][idx];
		const size = Math.abs(vv) / maxVar * 50;
		if (vv >= 0) {
			pdata[0][pi] = data[0][idx];
			pdata[1][pi] = data[1][idx];
			pdata[2][pi] = size + 6;
			pdata[3][pi] = data[3][idx];
			pi++;
		} else {
			ndata[0][ni] = data[0][idx];
			ndata[1][ni] = data[1][idx];
			ndata[2][ni] = size + 3;
			ndata[3][ni] = data[3][idx];
			ni++;
		}

	}
	console.timeEnd('restructure');
	plotInit();
}

function drawPoints(u, seriesIdx) {
	uPlot.orient(u, seriesIdx, (series, dataX, dataY, scaleX, scaleY, valToPosX, valToPosY, xOff, yOff, xDim, yDim, moveTo, lineTo, rect, arc) => {
		let d = u.data[seriesIdx];
		u.ctx.fillStyle = series.stroke();
		let deg360 = 2 * Math.PI;
		let p = new Path2D();
		for (let i = 0; i < d[0].length; i++) {
			let xVal = d[0][i];
			let yVal = d[1][i];
			let size = d[2][i] * devicePixelRatio;
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

function drawCircles(u, seriesIdx) {
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
	if (!ndata.length) return;
	plot.initCustom(style => {
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
					values: (u, vals) => vals.map(v => {
						const d = new Date(v * 1000);
						const day = String(d.getDate()).padStart(2, '0');
						const hour =  String(d.getHours()).padStart(2, '0');
						return day + '.' + hour;
					})
				},
				{
					label: 'asimptotic longitude, deg',
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
					stroke: 'rgba(0,255,255,1)',
					fill: 'rgba(0,255,255,0.5)',
					paths: drawPoints
				},
				{
					facets: [ { scale: 'x', auto: true }, { scale: 'y', auto: true } ],
					stroke: 'rgba(255,10,110,1)',
					fill: 'rgba(255,10,110,0.5)',
					paths: drawPoints
				}
			]
		};
	}, [ null, pdata, ndata ]);
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

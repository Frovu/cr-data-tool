import * as tabs from '../lib/tabsUtil.js';
import * as util from '../lib/util.js';
import * as plot from '../plot.js';
import uPlot from '../lib/uPlot.esm.js';
import * as qtree from '../lib/quadtree.js';

const URL = 'api/neutron/circles';
const params = util.storage.getObject('circles-params') || {
	from: new Date(2021, 10, 1).getTime() / 1000,
	to: new Date(2021, 11, 15).getTime() / 1000,
};
let pdata = [], ndata = [];
let stations = [], shifts = [], base = 0;
let qt = null;

let maxSize = 72;

export function receiveData(resp) {
	const slen = resp.shift.length, tlen = resp.time.length;
	if (tlen < 10) return;
	stations = resp.station, shifts = resp.shift, base = parseInt(resp.base);
	const data = Array.from(Array(4), () => new Array(slen*tlen));
	let maxVar = 0, posCount = 0, nullCount = 0;
	maxSize = 5 + plot.getPlotSize(false).height / 10;
	console.log('max size', maxSize);
	console.time('restructure');
	for (let ti = 0; ti < tlen; ++ti) {
		for (let si = 0; si < slen; ++si) {
			const time = resp.time[ti], vv = resp.variation[ti][si];
			const idx = ti*slen + si;
			if (vv < maxVar) maxVar = vv;
			if (vv == null) ++nullCount;
			else if (vv >= 0) ++posCount;
			data[0][idx] = time;
			data[1][idx] = (time / 86400 * 360 + resp.shift[si]) % 360 - 180;
			data[2][idx] = vv;
			data[3][idx] = si;
		}
	}
	maxVar = Math.abs(maxVar);
	if (maxVar < 8) maxVar = 8;
	ndata = Array.from(Array(5), () => new Array(slen*tlen - posCount - nullCount));
	pdata = Array.from(Array(5), () => new Array(posCount));
	let pi = 0, ni = 0, len = slen*tlen;
	for (let idx = 0; idx < len; ++idx) {
		const vv = data[2][idx];
		if (vv == null) continue;
		let size = Math.abs(vv) / maxVar * maxSize;
		if (size > maxSize) size = maxSize;
		if (vv >= 0) {
			pdata[0][pi] = data[0][idx];
			pdata[1][pi] = data[1][idx];
			pdata[2][pi] = size + 1;
			pdata[3][pi] = data[3][idx];
			pdata[4][pi] = vv;
			pi++;
		} else {
			ndata[0][ni] = data[0][idx];
			ndata[1][ni] = data[1][idx];
			ndata[2][ni] = size;
			ndata[3][ni] = data[3][idx];
			ndata[4][ni] = vv;
			ni++;
		}

	}
	console.timeEnd('restructure');
	plotInit();
}

function drawCircles(u, seriesIdx) {
	uPlot.orient(u, seriesIdx, (series, dataX, dataY, scaleX, scaleY, valToPosX, valToPosY, xOff, yOff, xDim, yDim) => {
		let strokeWidth = 1;
		let deg360 = 2 * Math.PI;
		let d = u.data[seriesIdx];

		console.time('circles');

		u.ctx.save();
		u.ctx.rect(u.bbox.left, u.bbox.top, u.bbox.width, u.bbox.height);
		u.ctx.clip();
		u.ctx.fillStyle = series.fill();
		u.ctx.strokeStyle = series.stroke();
		u.ctx.lineWidth = strokeWidth;

		let filtLft = u.posToVal(-maxSize / 2, scaleX.key);
		let filtRgt = u.posToVal(u.bbox.width / devicePixelRatio + maxSize / 2, scaleX.key);
		let filtBtm = u.posToVal(u.bbox.height / devicePixelRatio + maxSize / 2, scaleY.key);
		let filtTop = u.posToVal(-maxSize / 2, scaleY.key);
		for (let i = 0; i < d[0].length; i++) {
			let xVal = d[0][i];
			let yVal = d[1][i];
			let size = d[2][i] * devicePixelRatio;
			if (xVal >= filtLft && xVal <= filtRgt && yVal >= filtBtm && yVal <= filtTop) {
				let cx = valToPosX(xVal, scaleX, xDim, xOff);
				let cy = valToPosY(yVal, scaleY, yDim, yOff);
				u.ctx.moveTo(cx + size/2, cy);
				u.ctx.beginPath();
				u.ctx.arc(cx, cy, size/2, 0, deg360);
				u.ctx.fill();
				u.ctx.stroke();
				qt.add({
					x: cx - size/2 - strokeWidth/2 - u.bbox.left,
					y: cy - size/2 - strokeWidth/2 - u.bbox.top,
					w: size + strokeWidth,
					h: size + strokeWidth,
					sidx: seriesIdx,
					didx: i
				});
			}
		}
		console.timeEnd('circles');
		u.ctx.restore();
	});
}

function plotInit() {
	if (!ndata.length) return;
	plot.initCustom(style => {
		let hRect; // hovered
		const legendValue = u => {
			if (u.data == null || hRect == null)
				return '';
			const d = u.data[hRect.sidx];
			const stIdx = d[3][hRect.didx], lon = d[1][hRect.didx].toFixed(2);
			const time = new Date(d[0][hRect.didx] * 1000).toISOString().replace(/\..*|T/g, ' ');
			return `[ ${stations[stIdx]} ] v = ${d[4][hRect.didx]}%, aLon = ${lon} (${shifts[stIdx]}), time = ${time}`;
		};
		return {
			...plot.getPlotSize(false),
			padding: [0, 0, 0, 0],
			mode: 2,
			cursor: {
				drag: { x: false, y: false },
				dataIdx: (u, seriesIdx) => {
					if (seriesIdx == 1) {
						hRect = null;

						let dist = Infinity;
						let cx = u.cursor.left * devicePixelRatio;
						let cy = u.cursor.top * devicePixelRatio;

						qt.get(cx, cy, 1, 1, o => {
							if (qtree.pointWithin(cx, cy, o.x, o.y, o.x + o.w, o.y + o.h)) {
								let ocx = o.x + o.w / 2;
								let ocy = o.y + o.h / 2;

								let dx = ocx - cx;
								let dy = ocy - cy;

								let d = Math.sqrt(dx ** 2 + dy ** 2);

								// test against radius for actual hover
								if (d <= o.w / 2) {
									// only hover bbox with closest distance
									if (d <= dist) {
										dist = d;
										hRect = o;
									}
								}
							}
						});
					}
					return hRect && seriesIdx == hRect.sidx ? hRect.didx : null;
				},
				points: {
					size: (u, seriesIdx) => {
						return hRect && seriesIdx == hRect.sidx ? hRect.w / devicePixelRatio : 0;
					}
				}
			},
			hooks: {
				drawClear: [
					u => {
						const baseX = u.valToPos(base, 'x');
						u.ctx.save();
						u.ctx.strokeStyle = '#ffbb00';
						u.ctx.lineWidth = 1;
						u.ctx.beginPath();
						u.ctx.moveTo(u.bbox.left + baseX, u.bbox.top);
						u.ctx.lineTo(u.bbox.left + baseX, u.bbox.top + u.bbox.height);
						u.ctx.stroke();
						u.ctx.restore();

						qt = qt || new qtree.Quadtree(0, 0, u.bbox.width, u.bbox.height);
						qt.clear();
						u.series.forEach((s, i) => {
							if (i > 0)
								s._paths = null;
						});
					},
				]
			},
			axes: [
				{
					font: style.font,
					stroke: style.text,
					grid: { stroke: style.grid, width: 1 },
					ticks: { stroke: style.grid, width: 1 },
					space: 70,
					size: 40,
					values: (u, vals) => vals.map(v => {
						const d = new Date(v * 1000);
						const day = String(d.getDate()).padStart(2, '0');
						const hour =  String(d.getHours()).padStart(2, '0');
						return day + '\'' + hour;
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
					label: '+',
					facets: [ { scale: 'x', auto: true }, { scale: 'y', auto: true } ],
					stroke: 'rgba(0,255,255,1)',
					fill: 'rgba(0,255,255,0.5)',
					value: legendValue,
					paths: drawCircles
				},
				{
					label: '-',
					facets: [ { scale: 'x', auto: true }, { scale: 'y', auto: true } ],
					stroke: 'rgba(255,10,110,1)',
					fill: 'rgba(255,10,110,0.5)',
					value: legendValue,
					paths: drawCircles
				}
			]
		};
	}, [ null, pdata, ndata ]);
}

const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('circles-params', p)
});

const EVENTS = {
	'FD 2012-07-14': [ '2012-07-12', '2012-07-16' ],
	'FD 2012-09-03': [ '2012-09-01', '2012-09-06' ],
	'FD 2013-03-15': [ '2013-03-11', '2013-03-16' ],
	'FD 2013-04-14': [ '2013-04-11', '2013-04-16' ],
	'FD 2016-06-13': [ '2016-06-09', '2016-06-15' ],
	'FD 2021-10-04': [ '2021-11-01', '2021-11-05' ],
};

export function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Plot GLE precursors using stations ring method.<br>Yellow line shows base period (24h) start`)
	]);
	const timeInput = tabs.input('time', (from, to, force) => {
		params.from = from;
		params.to = to;
		query.params(params);
		if (force)
			query.fetch(params);
	}, { from: params.from, to: params.to, editable: true });
	tabs.fill('query', [
		timeInput.elem,
		tabs.input('select', opt => {
			const interval = EVENTS[opt].map(d => new Date(d));
			[ params.from, params.to ] = interval.map(d => d.getTime() / 1000);
			query.params(params);
			timeInput.set(...interval);
			query.fetch(params);
		}, { text: 'Select event:', options: Object.keys(EVENTS) }),
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

import * as tabs from '../lib/tabsUtil.js';
import * as util from '../lib/util.js';
import * as plot from '../plot.js';
import uPlot from '../lib/uPlot.esm.js';
import * as qtree from '../lib/quadtree.js';

const EVENTS = {
	'FD 2011-02-18': [ '2011-02-15', '2011-02-19' ],
	'FD 2012-07-14': [ '2012-07-12', '2012-07-16' ],
	'FD 2012-09-03': [ '2012-09-01', '2012-09-06' ],
	'FD 2013-03-15': [ '2013-03-11', '2013-03-16' ],
	'FD 2013-04-14': [ '2013-04-11', '2013-04-16' ],
	'FD 2016-06-13': [ '2016-06-09', '2016-06-15' ],
	'FD 2021-11-04': [ '2021-11-01', '2021-11-05' ],
	'FD 2022-05-20': [ '2022-05-15', '2022-05-22' ],
};

const URL = 'api/neutron/circles';
const params = util.storage.getObject('circles-params') || {
	from: new Date(2021, 10, 1).getTime() / 1000,
	to: new Date(2021, 10, 5).getTime() / 1000,
};
let pdata = [], ndata = [], prec_idx = [];
let resp, stations = [], shifts = [], base = 0;
let qt = null;
let aplot, mplot;
let clickCallback, baseCallback;

const MAX_VAR = 10;
let maxVar = MAX_VAR, variationShift = 0;

export function receiveData(data, clickCbk = null, baseCbk = null) {
	resp = data;
	stations = data.station, shifts = data.shift, base = parseInt(data.base);
	clickCallback = clickCbk;
	baseCallback = baseCbk;
	render();
}

function render() {
	if (!resp) return;
	const slen = resp.shift.length, tlen = resp.time.length;
	if (tlen < 10) return;
	const data = Array.from(Array(4), () => new Array(slen*tlen));
	let posCount = 0, nullCount = 0;
	maxVar = MAX_VAR;
	console.time('restructure');
	for (let ti = 0; ti < tlen; ++ti) {
		for (let si = 0; si < slen; ++si) {
			const time = resp.time[ti], vv = resp.variation[ti][si] + variationShift;
			const idx = ti*slen + si;
			// if (vv < maxVar) maxVar = vv;
			if (vv == null) ++nullCount;
			else if (vv >= 0) ++posCount;
			data[0][idx] = time;
			data[1][idx] = (time / 86400 * 360 + resp.shift[si]) % 360;
			data[2][idx] = vv;
			data[3][idx] = si;
		}
	}
	// maxVar = Math.abs(maxVar);
	// if (maxVar < MAX_VAR) maxVar = MAX_VAR;
	ndata = Array.from(Array(4), () => new Array(slen*tlen - posCount - nullCount));
	pdata = Array.from(Array(4), () => new Array(posCount));
	let pi = 0, ni = 0, len = slen*tlen;
	for (let idx = 0; idx < len; ++idx) {
		const vv = data[2][idx];
		if (vv == null) continue;
		if (vv >= 0) {
			pdata[0][pi] = data[0][idx];
			pdata[1][pi] = data[1][idx];
			pdata[2][pi] = vv;
			pdata[3][pi] = data[3][idx];
			pi++;
		} else {
			ndata[0][ni] = data[0][idx];
			ndata[1][ni] = data[1][idx];
			ndata[2][ni] = vv;
			ndata[3][ni] = data[3][idx];
			ni++;
		}
	}
	prec_idx = resp.precursor_idx;
	console.timeEnd('restructure');
	plotInit();
}

function drawCircles(u, seriesIdx) {
	uPlot.orient(u, seriesIdx, (series, dataX, dataY, scaleX, scaleY, valToPosX, valToPosY, xOff, yOff, xDim, yDim) => {
		let strokeWidth = 1;
		let deg360 = 2 * Math.PI;
		let d = u.data[seriesIdx];

		let maxSize = 5 + plot.getPlotSize(false).height / 10;
		console.log('max size', maxSize);
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
			let size = (Math.abs(d[2][i]) / maxVar * maxSize + 1) * devicePixelRatio;
			if (size > maxSize) size = maxSize;

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
	if (!clickCallback) clickCallback = plotClick;
	if (!ndata.length) return;
	if (mplot) mplot.destroy();
	mplot = plot.initCustom(style => {
		let hRect; // hovered
		const legendValue = u => {
			if (u.data == null || hRect == null)
				return '';
			const d = u.data[hRect.sidx];
			const stIdx = d[3][hRect.didx], lon = d[1][hRect.didx].toFixed(2);
			const time = new Date(d[0][hRect.didx] * 1000).toISOString().replace(/\..*|T/g, ' ');
			return `[ ${stations[stIdx]} ] v = ${d[2][hRect.didx].toFixed(2)}%, aLon = ${lon} (${shifts[stIdx]}), time = ${time}`;
		};
		return {
			...plot.getPlotSize(false),
			padding: [0, 0, 0, 0],
			mode: 2,
			// select: { over: false }, 
			cursor: {
				drag: { x: false, y: false, setScale: false },
				dataIdx: (u, seriesIdx) => {
					if (seriesIdx == 3) {
						return u.posToIdx(u.cursor.left * devicePixelRatio);
					}
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
						u.setSelect({
							left: u.valToPos(base, 'x'),
							top: 0,
							width: u.valToPos(base + 86400, 'x') - u.valToPos(base, 'x'),
							height: u.over.offsetHeight
						});
						qt = qt || new qtree.Quadtree(0, 0, u.bbox.width, u.bbox.height);
						qt.clear();
						u.series.forEach((s, i) => {
							if (i > 0)
								s._paths = null;
						});
					},
				],
				ready: [
					u => {
						let currentBase = base;
						const setSelect = (val) => u.setSelect({
							left: u.valToPos(val, 'x'),
							top: 0,
							width: u.valToPos(val + 86400, 'x') - u.valToPos(val, 'x'),
							height: u.over.offsetHeight
						});
						setSelect(currentBase);
						let dragBase, clickX, clickY, detailsIdx = null;
						u.over.addEventListener('mousemove', e => {
							if (dragBase) {
								const dragValue = u.posToVal(e.clientX, 'x') - u.posToVal(clickX, 'x');
								currentBase = Math.round((base + dragValue) / 3600) * 3600;
								if (currentBase < u.scales.x.min)
									currentBase = u.scales.x.min;
								if (currentBase > u.scales.x.max - 86400)
									currentBase = u.scales.x.max - 86400;

							}
							setSelect(currentBase);
						});
						u.over.addEventListener('mousedown', e => {
							clickX = e.clientX;
							clickY = e.clientY;
							dragBase = u.valToPos(base, 'x', true) < clickX && clickX < u.valToPos(base + 86400, 'x', true);
						});
						u.over.addEventListener('mouseup', e => {
							dragBase = false;
							if (currentBase !== base) {
								baseCallback && baseCallback(currentBase);
							}
							else if (Math.abs(e.clientX - clickX) + Math.abs(e.clientY - clickY) < 30) {
								detailsIdx = u.posToIdx(u.cursor.left * devicePixelRatio);
								if (detailsIdx != null)
									clickCallback(prec_idx[0][detailsIdx]);
							}
							clickX = clickY = null;
							setSelect(currentBase);
						});
						window.onkeydown = e => {
							if (detailsIdx !== null) {
								if (e.keyCode == 39)
									detailsIdx += 1;
								else if (e.keyCode == 37)
									detailsIdx -= 1;
								else
									return;
								if (detailsIdx < 0)
									detailsIdx = 0;
								else if (detailsIdx >= prec_idx[0].length)
									detailsIdx = prec_idx[0].length - 1;
								else
									clickCallback(prec_idx[0][detailsIdx]);
							}
						};
					}
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
						const day = String(d.getUTCDate()).padStart(2, '0');
						const hour =  String(d.getUTCHours()).padStart(2, '0');
						return day + '\'' + hour;
					})
				},
				{
					// label: 'asimptotic longitude, deg',
					scale: 'y',
					font: style.font,
					stroke: style.text,
					values: (u, vals) => vals.map(v => v.toFixed(0)),
					ticks: { stroke: style.grid, width: 1 },
					grid: { stroke: style.grid, width: 1 }
				},
				{
					scale: 'idx',
					show: false
				}
			],
			scales: {
				x: {
					time: false,
					range: (u, min, max) => [min, max],
				},
				y: {
					range: [-5, 365],
				},
				idx: {
					range: [ -.04, 3.62 ]
				}
			},
			series: [
				{ facets: [ { scale: 'x', auto: true } ] },
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
				},
				{
					scale: 'idx',
					label: 'idx',
					stroke: 'rgba(255,170,0,0.9)',
					facets: [ { scale: 'x', auto: true }, { scale: 'idx', auto: true } ],
					value: (u, v, si, di) => u.data[3][1][di] || 'NaN',
					paths: plot.linePaths(1.75)
				}
			]
		};
	}, [ prec_idx[0], pdata, ndata, prec_idx ]);
}

export function initDetailsPlot(body, parent) {
	if (aplot) aplot.destroy();
	const dt = new Date(body.time * 1000).toISOString().replace(/\..*|T/g, ' ');
	const width = parent.offsetWidth - 32;
	aplot = plot.initCustom(style => {
		return { // f=${body.angle.toFixed(2)}
			title: `[ ${dt}] i=${body.index.toFixed(2)} a=${body.amplitude.toFixed(2)}`,
			width, height: width,
			mode: 2,
			padding: [10, 0, 0, 0],
			legend: { show: false, live: false},
			cursor: {
				drag: { x: false, y: false }
			},
			hooks: { },
			axes: [
				{
					font: style.font,
					stroke: style.text,
					grid: { stroke: style.grid, width: 1 },
					ticks: { stroke: style.grid, width: 1 },
					values: (u, vals) => vals.map(v => v.toFixed(0)),
				},
				{
					scale: 'y',
					font: style.font,
					stroke: style.text,
					values: (u, vals) => vals.map(v => v.toFixed(1)),
					ticks: { stroke: style.grid, width: 1 },
					grid: { stroke: style.grid, width: 1 }
				}
			],
			scales: {
				x: {
					time: false,
					range: [0, 365],
				},
				y: {
					range: (u, min, max) => [min, max],
				}
			},
			series: [
				{},
				{
					stroke: 'rgba(255,10,110,1)',
					paths:  plot.pointPaths(10)
				},
				{
					stroke: 'rgb(100,0,200)',
					paths: plot.linePaths(2)
				}
			]
		};
	}, [ null, [body.x, body.y], [body.fnx, body.fny] ], parent);
}

async function plotClick(time) {
	console.log('%cclick', 'color: #f0f', time);
	let url = `${URL}?from=${params.from}&to=${params.to}&details=${time}`;
	if (params.window) url += `&window=${params.window}`;
	if (params.minamp) url += `&minamp=${params.minamp}`;
	const res = await fetch(url);
	if (res.status == 200) {
		const body = await res.json();
		console.log(body);
		if (!body.time) return tabs.showResult(false);
		tabs.showResult();
		const tab = document.getElementById('result-tab');
		initDetailsPlot(body, tab);
	} else {
		console.log('%cfailed to get details:', 'color: #f0a', res.status);
	}
}

const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('circles-params', p)
});

export function setVariationShift(shift) {
	variationShift = shift;
	render();
}

export function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Plot FD precursors using ring of stations method.<br>Purple line depicts base period (24h) start`)
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
		tabs.text('<p>'),
		tabs.input('text', val => {
			if (isNaN(parseInt(val)))
				val = null;
			params.window = val;
			query.params(params);
		}, { value: params.window, placeholder: '1 < w < 12', label: 'Window (h): ', width: 96 }),
		tabs.text('<p>'),
		tabs.input('text', val => {
			if (isNaN(parseFloat(val)))
				val = null;
			params.minamp = val;
			query.params(params);
		}, { value: params.minamp, placeholder: 'a > 0', label: 'Amp cutoff: ', width: 96 }),
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
	tabs.showResult(false);
}
import * as plot from '../plot.js';
import * as tabs from '../tabsUtil.js';

const LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20, 10];
const params = {
	from: Math.floor(Date.now()/1000) - 86400*375,
	to: Math.floor(Date.now()/1000) - 86400*10,
	lat: 55.47,
	lon: 37.32
};
let data;
let activeSeries = [0, 2];
// activeSeries = LEVELS.map((a,i)=>i)
let dataFetch;
let queryBtn;
// let progress;

function encodeParams(obj) {
	const keys = Object.keys(obj);
	return keys.length ? '?' + keys.map(k => `${k}=${obj[k]}`).join('&') : '';
}

async function tryFetch() {
	const progress = document.getElementById('progress');
	const resp = await fetch(`api/temp/${encodeParams(params)}`).catch(()=>{});
	if (resp && resp.status === 200) {
		const body = await resp.json().catch(()=>{});
		if (body.status === 'ok') {
			progress.innerHTML = 'done!';
			return body;
		} else if (body.status === 'busy') {
			progress.innerHTML = body.download ? `Downloading: ${(100*body.download).toFixed(0)} %` : 'Calculating';
		} else if (body.status === 'unknown') {
			// TODO:
		}
	} else {
		console.log('request failed', resp && resp.status);
	}
}

function startFetch() {
	return new Promise(resolve => {
		tryFetch().then(ok => {
			if (!ok) {
				dataFetch = setInterval(() => {
					tryFetch().then(okk => {
						if (okk) {
							resolve(okk);
							clearInterval(dataFetch);
							dataFetch = null;
						}
					});
				}, 1000);
			} else {
				resolve(ok);
			}
		});
	});
}

function stopFetch() {
	if (dataFetch) {
		clearInterval(dataFetch);
		dataFetch = null;
	}
}

function receiveData(resp) {
	const rows = resp.data, len = resp.data.length, rowLen = resp.fields.length;
	const idx = Array(rowLen);
	['time'].concat(LEVELS).forEach((field, i) => {
		idx[resp.fields.indexOf(field)] = i;
	});
	data = resp.fields.map(() => Array(len));
	for (let i = 0; i < len; ++i) {
		for (let j = 0; j < rowLen; ++j) {
			data[idx[j]][i] = rows[i][j];
		}
	}
	plotData();
}

function color(idx) {
	const inc = 15*idx/3;
	const base = [`255,${inc+50},${inc+50}`, `${inc},255,${inc}`, `${inc-100},${inc+255},255`][idx%3];
	return `rgba(${base},1)`;
}

function plotInit() {
	const series = ['time'].concat(activeSeries.map(col => {return {
		scale: 'K',
		label: `h=${LEVELS[col].toFixed(0)}mb`,
		color: color(col),
		precision: 1
	};}));
	const axes = ['time'].concat({
		scale: 'K'
	});
	plot.init(series, axes);
	plotData();
}

function plotData() {
	if (data) {
		const plotData = [data[0]].concat(activeSeries.map(col => data[col+1]));
		plot.data(plotData);
	}
}

async function fetchData() {
	const data = await startFetch();
	if (data) receiveData(data);
}

function viewSeries(idx, show) {
	if (show) {
		if (activeSeries.includes(idx)) return;
		activeSeries.push(idx);
		activeSeries = activeSeries.sort((a, b) => a-b);
	} else {
		activeSeries = activeSeries.filter(s => s !== idx);
	}
	plotInit();
}

export function initTabs() {
	queryBtn = tabs.input('query', fetchData);
	const viewSelectors = LEVELS.map((lvl, i) => {
		const div = document.createElement('div');
		const box = document.createElement('input');
		const lbl = document.createElement('label');
		div.classList.add('view-option');
		const id = `ser-${lvl}mb`;
		box.setAttribute('type', 'checkbox');
		if (activeSeries.includes(i)) box.setAttribute('checked', true);
		box.setAttribute('id', id);
		lbl.setAttribute('for', id);
		lbl.setAttribute('style', `border-color: ${color(i)};`);
		lbl.innerHTML = `h = ${lvl} mb<span class="color-box" style="background-color: ${color(i)};"></span>`;
		div.append(box, lbl);
		div.addEventListener('change', () => {
			viewSeries(i, document.getElementById(id).checked);
		});
		return div;
	});
	tabs.fill('query', [
		// tabs.input('time', (from, to) => {
		//
		// }),
		queryBtn
	]);
	tabs.fill('view', viewSelectors);
	tabs.disable('tools');
	tabs.disable('export');
}

export function load() {
	plotInit();
	fetchData();
}

export function unload() {
	stopFetch();
}

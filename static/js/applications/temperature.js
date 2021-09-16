import * as plot from '../plot.js';
import * as tabs from '../tabsUtil.js';

const LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20, 10];
const params = {
	from: Date.now()/1000 - 86400*375,
	to: Date.now()/1000 - 86400*10,
	lat: 55.47,
	lon: 37.32
};
let data;
let columns = [0, 1, 2];
let dataFetch;
let queryBtn;
let progress;

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
	console.log(resp);
	const rows = resp.rows, len = resp.rows.length, rowLen = resp.fields.length;
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
	return idx < 3 ? ['red', 'green', 'blue'][idx] : 'gray';
}

function plotInit() {
	const series = ['time'].concat(columns.map(col => {return {
		scale: 'K',
		label: `h=${LEVELS[col].toFixed(0)}mb`,
		color: color(col)
	};}));
	const axes = ['time'].concat({
		scale: 'K',
		precision: 1
	});
	plot.init(series, axes);
}

function plotData() {
	if (data) {
		const plotData = [data[0]].concat(columns.map(col => data[col+1]));
		plot.data(plotData);
	}
}

export function initTabs() {
	queryBtn = tabs.input('query', async () => {
		const data = await startFetch();
		if (data) receiveData(data);
	});
	tabs.fill('query', [
		tabs.input('time', (from, to) => {

		}),
		queryBtn
	]);
	tabs.disable('tools');
	tabs.disable('export');
}

export function load() {
	plotInit();
}

export function unload() {
	stopFetch();
}

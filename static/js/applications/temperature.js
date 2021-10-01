import * as plot from '../plot.js';
import * as tabs from '../tabsUtil.js';

const LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20, 10];
const COLUMNS = ['t2'].concat(LEVELS.map(l => `t_${l.toFixed(0)}mb`));
const DEFAULT_DELTA = 86400*30; // 86400*365
const params = {
	from: Math.floor(Date.now()/1000) - 86400*10 - DEFAULT_DELTA,
	to: Math.floor(Date.now()/1000) - 86400*10,
	lat: 55.47,
	lon: 37.32
};
let data;
let activeSeries = [0, 1, 2];
// activeSeries = LEVELS.map((a,i)=>i)
let fetchOngoing = false;
let dataFetch;
let queryBtn;
const unitOptions = ['K', '°C'];
let temperatureUnit = 'K';
let settingsChangedDuringFetch;
// let progress;

export function encodeParams(obj) {
	const keys = Object.keys(obj);
	return keys.length ? '?' + keys.map(k => `${k}=${obj[k]}`).join('&') : '';
}

async function tryFetch(param, status) {
	const resp = await fetch(`api/temp/${encodeParams(param)}`).catch(()=>{});
	if (resp && resp.status === 200) {
		const body = await resp.json().catch(()=>{});
		console.log('resp:', body);
		if (body.status === 'ok') {
			status.innerHTML = 'Done!';
			return body;
		} else if (body.status === 'busy') {
			status.innerHTML = body.download ? `Downloading: ${(100*body.download).toFixed(0)} %` : 'Calculating...';
		// } else if (body.status === 'unknown') {
		} else if (body.status === 'accepted') {
			status.innerHTML = 'Accepted';
		} else {
			status.innerHTML = 'Error..';
		}
	} else {
		console.log('request failed', resp && resp.status);
	}
}

function startFetch(param, status) {
	return new Promise(resolve => {
		tryFetch(param, status).then(ok => {
			if (!ok) {
				dataFetch = setInterval(() => {
					tryFetch(param, status).then(okk => {
						if (okk) {
							resolve(okk);
							clearInterval(dataFetch);
							dataFetch = null;
						}
					});
				}, 2000);
			} else {
				resolve(ok);
			}
		});
	});
}

export function stopFetch() {
	if (dataFetch) {
		clearInterval(dataFetch);
		dataFetch = null;
	}
}

export function settingsChanged(status=queryBtn) {
	if (!fetchOngoing) {
		status.classList.add('active');
		status.innerHTML = 'Query data';
	} else {
		settingsChangedDuringFetch = true;
	}
}

function receiveData(resp) {
	const rows = resp.data, len = resp.data.length;
	const fields = ['time'].concat(COLUMNS);
	const fieldsLen = Math.min(resp.fields.length, fields.length)
	const idx = Array(fields.length);
	fields.forEach((field, i) => {
		console.log(field, resp.fields.indexOf(field))
		idx[resp.fields.indexOf(field)] = i;
	});
	data = fields.map(() => Array(len));
	for (let i = 0; i < len; ++i) {
		for (let j = 0; j < rowLen; ++j) {
			if ()
			data[idx[j]][i] = rows[i][j];
		}
	}
	plotData();
}

function color(idx) {
	if (idx === 0)
		return 'rgba(155,0,200,1)';
	const inc = 15*idx/3;idx[j]
	const base = [`${inc},255,${inc}`, `255,${inc+50},${inc+50}`, `${inc-100},${inc+255},255`][idx%3];
	return `rgba(${base},1)`;
}

function plotInit(full=true) {
	const transform = temperatureUnit!=='K' && (t => t-273.15);
	const series = activeSeries.map(col => {return {
		scale: temperatureUnit,
		label: COLUMNS[col],
		color: color(col),
		precision: 1,
		transform
	};});
	if (full) {
		const axes = [{ scale: temperatureUnit, transform }];
		plot.init(axes);
	}
	plot.series(series);
	plotData(full);
}

function plotData(resetScales=true) {
	if (data) {
		const plotData = [data[0]].concat(activeSeries.map(col => data[col+1]));
		plot.data(plotData, resetScales);
	}
}

export async function fetchData(param=params, receiver=receiveData, status=queryBtn) {
	if (!fetchOngoing) {
		status.classList.add('ongoing');
		status.innerHTML = 'Query...';
		status.classList.remove('active');
		fetchOngoing = true;
		settingsChangedDuringFetch = false;
		const data = await startFetch(param, status);
		if (data) receiver(data);
		fetchOngoing = false;
		status.classList.remove('ongoing');
		if (settingsChangedDuringFetch) {
			setInterval(() => {
				status.classList.add('active');
				status.innerHTML = 'Query data';
			}, 300);
		}
	}
}

function viewSeries(idx, show) {
	if (show) {
		if (activeSeries.includes(idx)) return;
		activeSeries.push(idx);
		activeSeries = activeSeries.sort((a, b) => a-b);
	} else {
		activeSeries = activeSeries.filter(s => s !== idx);
	}
	plotInit(false);
}

export async function fetchStations() {
	const resp = await fetch('api/temp/stations').catch(()=>{});
	if (!resp || resp.status !== 200) return null;
	return (await resp.json()).list;
}

export function initTabs() {
	queryBtn = tabs.input('query', ()=>fetchData());
	const fillSpaces = s => s + Array(11).fill('&nbsp;').slice(s.length).join('');
	const viewSelectors = COLUMNS.map((col, i) => {
		const div = document.createElement('div');
		const box = document.createElement('input');
		const lbl = document.createElement('label');
		div.classList.add('view-option');
		const id = `ser-${col}`;
		box.setAttribute('type', 'checkbox');
		if (activeSeries.includes(i)) box.setAttribute('checked', true);
		box.setAttribute('id', id);
		lbl.setAttribute('for', id);
		lbl.setAttribute('style', `border-color: ${color(i)};`);
		lbl.innerHTML = `${fillSpaces(col.replace('_', ', h=').replace('t2', 't2, station'))}<span class="color-box" style="background-color: ${color(i)};"></span>`;
		div.append(box, lbl);
		div.addEventListener('change', () => {
			viewSeries(i, document.getElementById(id).checked);
		});
		return div;
	}).concat(tabs.input('switch', unit => {
		temperatureUnit = unit;
		plotInit();
	}, { options: unitOptions, text: 'Unit: ' }));
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Application retrieves atmospheric temperature data of <a href="https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html">NCEP/NCAR Reanalysis project</a> and interpolates it for given coordinates and for 1 hour time period.
Resulting data consists of 18 series of temperature at certain height.
<h4>Usage</h4>
The button on "Query" tab indicates your data query progress.
When query parameters are changed, the button becomes highlighted.`)
	]);
	fetchStations().then(ss => {
		tabs.fill('query', [
			!ss ? tabs.text('Stations failed to load, please refresh tab') :
				tabs.input('station', (lat, lon) => {
					params.lat = lat;
					params.lon = lon;
					settingsChanged();
				}, { text: 'in', list: ss, lat: params.lat, lon: params.lon }),
			tabs.input('time', (from, to, force) => {
				params.from = Math.floor(from.getTime() / 1000);
				params.to = Math.floor(to.getTime() / 1000);
				if (force)
					fetchData();
				else
					settingsChanged();
			}, { from: new Date(params.from*1000), to: new Date(params.to*1000) }),
			queryBtn
		]);
	});
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

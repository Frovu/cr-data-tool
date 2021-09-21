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
let fetchOngoing = false;
let dataFetch;
let queryBtn;
const unitOptions = ['K', '°C'];
let temperatureUnit = 'K';
let settingsChangedDuringFetch;
// let progress;

function encodeParams(obj) {
	const keys = Object.keys(obj);
	return keys.length ? '?' + keys.map(k => `${k}=${obj[k]}`).join('&') : '';
}

async function tryFetch() {
	const resp = await fetch(`api/temp/${encodeParams(params)}`).catch(()=>{});
	if (resp && resp.status === 200) {
		const body = await resp.json().catch(()=>{});
		console.log('resp:', body);
		if (body.status === 'ok') {
			queryBtn.innerHTML = 'Done!';
			return body;
		} else if (body.status === 'busy') {
			queryBtn.innerHTML = body.download ? `Downloading: ${(100*body.download).toFixed(0)} %` : 'Calculating...';
		// } else if (body.status === 'unknown') {
		} else if (body.status === 'accepted') {
			queryBtn.innerHTML = 'Accepted';
		} else {
			queryBtn.innerHTML = 'Error..';
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

function settingsChanged() {
	if (!fetchOngoing) {
		queryBtn.classList.add('active');
		queryBtn.innerHTML = 'Query data';
	} else {
		settingsChangedDuringFetch = true;
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

function plotInit(full=true) {
	const transform = temperatureUnit!=='K' && (t => t-273.15);
	const series = ['time'].concat(activeSeries.map(col => {return {
		scale: temperatureUnit,
		label: `h=${LEVELS[col].toFixed(0)}mb`,
		color: color(col),
		precision: 1,
		transform
	};}));
	if (full) {
		const axes = ['time'].concat({ scale: temperatureUnit, transform});
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

async function fetchData() {
	if (!fetchOngoing) {
		queryBtn.classList.add('ongoing');
		queryBtn.innerHTML = 'Query...';
		queryBtn.classList.remove('active');
		fetchOngoing = true;
		settingsChangedDuringFetch = false;
		const data = await startFetch();
		if (data) receiveData(data);
		fetchOngoing = false;
		queryBtn.classList.remove('ongoing');
		if (settingsChangedDuringFetch) {
			setInterval(() => {
				queryBtn.classList.add('active');
				queryBtn.innerHTML = 'Query data';
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

async function fetchStations() {
	const resp = await fetch('api/temp/stations').catch(()=>{});
	if (!resp || resp.status !== 200) return null;
	return (await resp.json()).list;
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

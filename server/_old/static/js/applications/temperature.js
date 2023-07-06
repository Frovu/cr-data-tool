import * as tabs from '../lib/tabsUtil.js';
import * as util from '../lib/util.js';
import * as plot from '../plot.js';

const URL = 'api/temperature';
const LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20, 10];
const COLUMNS = ['t2', 't_mass_avg'].concat(LEVELS.map(l => `t_${l.toFixed(0)}mb`));
const DEFAULT_DELTA = 86400*60; // 86400*365
const params = util.storage.getObject('temperature-params') || {
	from: Math.floor(Date.now()/1000) - 86400*10 - DEFAULT_DELTA,
	to: Math.floor(Date.now()/1000) - 86400*10,
	lat: 55.47,
	lon: 37.32
};
let data;
let activeSeries = [0, 1, 2];
const unitOptions = ['K', '°C'];
let temperatureUnit = '°C';

function receiveData(resp) {
	const rows = resp.data, len = resp.data.length;
	exprt.setData(resp.data, resp.fields);
	const fields = ['time'].concat(COLUMNS);
	const idx = Array(fields.length);
	resp.fields.forEach((field, i) => {
		const index = fields.indexOf(field);
		if (index >= 0)
			idx[index] = i;
	});
	data = fields.map(() => Array(len));
	for (let i = 0; i < len; ++i) {
		for (let j = 0; j < fields.length; ++j) {
			data[j][i] = rows[i][idx[j]];
		}
	}
	plotData();
}

function color(idx) {
	if (idx === 0)
		return 'rgba(155,0,200,1)';
	if (idx === 1)
		return 'rgba(200,50,0,1)';
	const inc = 15*idx/3;
	const base = [`${inc},255,${inc}`, `255,${inc+50},${inc+50}`, `${inc-100},${inc+255},255`][(idx-1)%3];
	return `rgba(${base},0.8)`;
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
		const axes = [{ scale: temperatureUnit, transform, size: 54}];
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
	const resp = await fetch(`${URL}/stations`).catch(()=>{});
	if (!resp || resp.status !== 200) return null;
	return (await resp.json()).list;
}

const exprt = tabs.exportTab(URL, params);
const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => {
		util.storage.setObject('temperature-params', p);
		exprt.setParams(p);
	}
});

export async function initTabs() {
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
		const name = col.includes('mb') ? col.replace('_', ', h=') : col;
		lbl.innerHTML = `${fillSpaces(name.replace('t2', 't2, station'))}<span class="color-box" style="background-color: ${color(i)};"></span>`;
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
	const stations = await fetchStations();
	tabs.fill('query', [
		!stations ? tabs.text('Stations failed to load, please refresh tab') :
			tabs.input('station', (lat, lon) => {
				params.lat = lat;
				params.lon = lon;
				query.params(params);
			}, { text: 'in', list: stations, lat: params.lat, lon: params.lon }),
		tabs.input('time', (from, to, force) => {
			params.from = from;
			params.to = to;
			query.params(params, force);
		}, { from: params.from, to: params.to }),
		query.el
	]);
	tabs.fill('view', viewSelectors);
	tabs.fill('export', [exprt.el]);

	if (stations) {
		const stationEdit = document.createElement('details');
		stationEdit.innerHTML = '<summary><u>Edit stations</u> (Admin)</summary><p>';
		const s = stations[0];
		const stationParams = { name: s.name, lat: s.lat, lon: s.lon, description: s.desc || '' };
		const eraseParams = { lat: params.lat, lon: params.lon, from: params.from, to: params.to };
		const eraseBtn = tabs.input('query', () => {}, {
			url: `${URL}/delete`, text: 'Erase', params: () => eraseParams
		});
		const editBtn = tabs.input('query', () => {}, {
			url: `${URL}/stations`, text: 'Edit/Create', params: () => stationParams, method: 'POST'
		});
		const stName = tabs.input('text', val => {
			stationParams.name = val;
		}, { value: s.name, label: 'Name:' });
		const stLat = tabs.input('text', val => {
			stationParams.lat = val;
		}, { value: s.lat, label: 'lat=' });
		const stLon = tabs.input('text', val => {
			stationParams.lon = val;
		}, { value: s.lon, label: 'lon=' });
		const stDesc = tabs.input('text', val => {
			stationParams.description = val;
		}, { value: s.desc, label: 'Description:', width: 256 });
		stationEdit.append(stName, stLat, stLon, tabs.text('<p>'), stDesc, tabs.text('<p>'), editBtn.elem);
		stationEdit.classList.add('station-input');
		tabs.fill('tools', [
			tabs.text('<h4>Erase data</h4><p>Delete data from server cache, forcing new calculation to be run. Recalculation may fix some data issues.</p>'),
			tabs.input('station', (lat, lon, name, desc) => {
				eraseParams.lat = lat;
				eraseParams.lon = lon;
				stLat.children[1].value = stationParams.lat = lat;
				stLon.children[1].value = stationParams.lon = lon;
				stName.children[1].value = stationParams.name = name;
				stDesc.children[1].value = stationParams.description = desc;
			}, { text: 'station', list: stations, lat: eraseParams.lat, lon: eraseParams.lon }),
			tabs.input('time', (from, to) => {
				eraseParams.from = from;
				eraseParams.to = to;
			}, { from: eraseParams.from, to: eraseParams.to }),
			eraseBtn.elem,
			tabs.text('<p>Note: To perform this action you should be authorized and have certain permission.</p><p>'),
			stationEdit
		]);
	}
	query.fetch(params);
}

export function load() {
	plotInit();
	plotData();
}

export function unload() {
	if (query)
		query.stop();
}
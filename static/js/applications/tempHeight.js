import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';
import * as temp from './temperature.js';

const URL = 'api/temperature';
const LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20, 10].reverse();
const params = util.storage.getObject('tempHeight-params') || {
	only: 'model',
	lat: 55.47,
	lon: 37.32,
	from: Math.floor(Date.now()/1000) - 86400*10
};
params.to = params.from + 3600;
let temperatureUnit = 'K';
let data;

function receiveData(resp) {
	const row = resp.data[0];
	if (!row) return console.error('empty response');
	data = [];
	LEVELS.forEach(lvl => {
		data.push(row[resp.fields.indexOf(`t_${lvl.toFixed(0)}mb`)]);
	});
	plot.data([LEVELS, data]);
}

function plotInit() {
	const transform = temperatureUnit!=='K' && (t => t-273.15);
	plot.init([
		{ scale: 'mb', side: 3, size: 70 },
		{ scale: temperatureUnit, transform, side: 2, space: 70 }
	], false, {
		mb: {
			range: [0, 1000],
			time: false,
			dir: -1,
			ori: 1
		},
		[temperatureUnit]: {
			dir: 1,
			ori: 0
		}
	}, [
		{
			scale: 'mb',
			label: 'Height',
			// color: null
		}, {
			scale: temperatureUnit,
			label: 'Temperature',
			color: 'red',
			width: 3,
			precision: 1,
			paths: 'spline',
			transform
		}
	]);
	if (data) plot.data([LEVELS, data]);
}

const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('tempHeight-params', p)
});

export function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Build atmospheric temperature lapse curve using <a href="https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html">NCEP/NCAR Reanalysis project</a> data.<br>
Refer to "Temperature" app for more details`)
	]);
	temp.fetchStations().then(ss => {
		tabs.fill('query', [
			!ss ? tabs.text('Stations failed to load, please refresh tab') :
				tabs.input('station', (lat, lon) => {
					params.lat = lat;
					params.lon = lon;
					query.params(params);
				}, { text: 'in', list: ss, lat: params.lat, lon: params.lon }),
			tabs.input('timestamp', (date, force) => {
				params.from = date;
				params.to = params.from + 3600;
				query.params(params, force);
			}, { value: params.from }),
			query.el
		]);
	});
	tabs.fill('view', [
		tabs.input('switch', unit => {
			temperatureUnit = unit;
			plotInit();
		}, { options: ['K', '°C'], text: 'Unit: ' })
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

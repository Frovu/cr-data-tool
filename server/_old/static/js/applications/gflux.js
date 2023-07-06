import * as tabs from '../lib/tabsUtil.js';
import * as util from '../lib/util.js';
import * as plot from '../plot.js';
import * as temp from './temperature.js';

const URL = 'api/temperature/gflux';
const params = {
	from: new Date(2022, 2, 1).getTime() / 1000,
	to: new Date(2022, 2, 12).getTime() / 1000,
	lat: 55.47,
	lon: 37.32
};
let data;

function receiveData(resp) {
	const rows = resp.data, len = resp.data.length;
	data = [ Array(len),  Array(len) ];
	for (let i = 0; i < len; ++i) {
		data[0][i] = rows[i][0];
		data[1][i] = rows[i][1];
	}
	plot.data(data);
}

function plotInit() {
	plot.init([{scale: ' w/m^2', size: 80}]);
	plot.series([{
		scale: ' w/m^2',
		label: 'gflux',
		color: 'rgba(170,255,0,1)',
		precision: 2
	}]);
	if (data) plot.data(data);
}
const query = util.constructQueryManager(URL, {
	data: receiveData
});

export async function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Ground heat flux`)
	]);
	const stations = await temp.fetchStations();
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
			query.params(params);
			if (force)
				query.fetch(params);
		}, { from: params.from, to: params.to }),
		query.el
	]);
	query.fetch(params);
}

export function load() {
	plotInit(data);
}

export function unload() {
	if (query)
		query.stop();
}

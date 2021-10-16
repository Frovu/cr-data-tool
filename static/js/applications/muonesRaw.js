import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';

const SUPPORTED = [ 'Moscow' ];
const URL_BASE = 'api/muones/';
const params = util.getObject('muonesRaw-params') || {
	from: Math.floor(Date.now()/1000) - 86400*10 - 86400*60,
	to: Math.floor(Date.now()/1000) - 86400*10,
	station: 'Moscow'
};
let data;

function receiveData(resp) {
	const row = resp.data[0];
	data = [];
	LEVELS.forEach(lvl => {
		data.push(row[resp.fields.indexOf(`t_${lvl.toFixed(0)}mb`)]);
	});
	plot.data([LEVELS, data]);
}

function plotInit() {
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
	if (data) plot.data([LEVELS, data]);
}
const query = util.constructQueryManager(URL_BASE, {
	dataCallback: receive
});

export function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Get raw data of local muones telescope.<br>
Only supported for: ${SUPPORTED}`)
	]);
	tabs.fill('query', [
		tabs.input('station-only', (station) => {
			params.station = station;
			query.params(params);
		}, { text: 'station: ', list: SUPPORTED }),
		tabs.input('time', (from, to, force) => {
			params.from = from;
			params.to = to;
			query.params(params);
			if (force)
				query.fetch(params);
		}, { from: params.from, to: params.to }),
		query.buttonEl
	]);
	tabs.disable('view');
	tabs.disable('tools');
	tabs.disable('export');
}

export function load() {
	plotInit();
	query.fetch(params);
}

export function unload() {
	if (query)
		query.stopFetch();
}

import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';

const FIELDS = {
	time: 'time',
	n_v_raw: {
		label: 'n_v_raw',
		scale: 'n',
		color: 'rgba(0,0,255,0.5)',
		nounit: true
	},
	n_v: {
		label: 'n_v',
		scale: 'n',
		color: 'rgba(255,0,0,1)',
		width: 2,
		nounit: true
	},
	pressure: {
		label: 'p',
		scale: 'mb',
		color: 'rgba(200,0,200,0.7)',
		precision: 1
	},
	T_m: {
		label: 't_mass_avg',
		scale: 'K',
		color: 'rgba(255,155,50,1)',
		precision: 1
	},
};
const URL = 'api/muones';
const params = util.storage.getObject('muones-params') || {
	from: Math.floor(Date.now()/1000) - 86400*3 - 86400*365,
	to: Math.floor(Date.now()/1000) - 86400*3,
	station: 'Moscow',
	period: 3600
};
let data;

function receiveData(resp) {
	const rows = resp.data, len = resp.data.length;
	const fields = Object.keys(FIELDS);
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
	plot.data(data);
}

function plotInit() {
	const series = Object.values(FIELDS).filter(f => f !== 'time');
	const axes = [
		{ scale: 'n' , nounit: true },
		{ scale: 'mb', side: 1, size: 70 },
		{ scale: 'K', show: false }
	];
	plot.init(axes);
	plot.series(series);
	if (data) plot.data(data);
}
const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('muones-params', p)
});

async function fetchStations() {
	const resp = await fetch('api/muones/stations').catch(()=>{});
	if (!resp || resp.status !== 200) return null;
	return (await resp.json()).list;
}

export async function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Get corrected muones data.
WIP<br>
`)
	]);
	const stations = (await fetchStations() || []).map(s => s.name);
	const sText = stations ? stations.join() : 'Stations failed to load, refresh tab please.';
	const periods = ['1 hour', '1 minute'];
	tabs.fill('query', [
		stations ?
			tabs.input('station-only', (station) => {
				params.station = station;
				plotInit();
				query.params(params);
			}, { text: 'station:', list: stations }) :
			tabs.text(sText),
		tabs.input('switch', per => {
			params.period = per.includes('minute') ? 60 : 3600;
			query.params(params);
		}, { options: params.period===60?periods.reverse():periods, text: 'period: ' }),
		tabs.input('time', (from, to, force) => {
			params.from = from;
			params.to = to;
			query.params(params);
			if (force)
				query.fetch(params);
		}, { from: params.from, to: params.to }),
		query.el
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
		query.stop();
}

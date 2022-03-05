import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';

const FIELDS = {
	time: 'time',
	source: {
		label: 'source',
		scale: 'n',
		color: 'rgba(60,10,150,0.5)',
		nounit: true
	},
	corrected: {
		label: 'corrected',
		scale: 'n',
		color: 'rgba(255,10,60,1)',
		nounit: true
	},
	pressure: {
		label: 'pressure',
		scale: 'mb',
		color: 'rgba(200,0,200,0.6)',
		precision: 1
	},
	T_m: {
		label: 'temperature',
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
	coefs: 'recalc',
	channel: 'V',
	period: 3600
};
let data;
let info;

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
	info = resp.info;
	plotInit();
}

function plotInit() {
	const series = Object.values(FIELDS).filter(f => f !== 'time');
	const axes = [
		{ scale: 'n' , nounit: true },
		{ scale: 'mb', side: 1, size: 70 },
		{ scale: 'K', show: false }
	];
	const cl = info && Math.floor(info.coef_per_length/86400);
	const c_pr = info && info.coef_pressure ? `c_pr=${info.coef_pressure.toFixed(5)} ` : '';
	const title = info && `${params.station}:${params.channel} ${c_pr}c_tm=${info.coef_temperature.toFixed(5)} cl=${cl}d`;
	plot.init(axes, true, null, null, title);
	plot.series(series);
	if (data) plot.data(data);
}
const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('muones-params', p)
});

async function fetchStations() {
	const resp = await fetch(URL + '/stations').catch(()=>{});
	if (!resp || resp.status !== 200) return null;
	return (await resp.json()).list;
}

export async function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Temperature corrected muons data.
Correction is performed via mass-average temperature method.<br>
`)
	]);
	const stations = await fetchStations() || [];
	const sText = stations ? stations.join() : 'Stations failed to load, refresh tab please.';
	// const periods = ['1 hour', '1 minute'];
	tabs.fill('query', [
		stations ?
			tabs.input('station-channel', (station, channel) => {
				params.station = station;
				params.channel = channel;
				plotInit();
				query.params(params);
			}, { text: 'station:', list: stations, station: params.station, channel: params.channel }) :
			tabs.text(sText),
		// tabs.input('switch', per => {
		// 	params.period = per.includes('minute') ? 60 : 3600;
		// 	query.params(params);
		// }, { options: params.period===60?periods.reverse():periods, text: 'period: ' }),
		tabs.input('switch', opt => {
			params.coefs = opt;
			query.params(params);
		}, { options: ['recalc', 'saved'], text: 'coefs: ' }),
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

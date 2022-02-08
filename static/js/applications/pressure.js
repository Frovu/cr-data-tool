import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';

const FIELDS = {
	Moscow: {
		time: 'time',
		muon: {
			label: 'BMP280',
			scale: 'mb',
			color: 'rgba(0,255,255,1)',
			precision: 2
		},
		rmp: {
			label: 'MD-20',
			scale: 'mb',
			color: 'rgba(255,100,10,1)',
			precision: 2
		},
		fcrl: {
			label: 'BPC-1M',
			scale: 'mb',
			color: 'rgba(255,10,100,1)',
			precision: 2
		}
	}
};
const SUPPORTED = Object.keys(FIELDS);
const URL = 'api/muones/pressure';
const params = util.storage.getObject('pressure-params') || {
	from: Math.floor(Date.now()/1000) - 86400*7,
	to: Math.floor(Date.now()/1000) - 86400,
	station: 'Moscow'
};
let data;

function receiveData(resp) {
	const rows = resp.data, len = resp.data.length;
	const fields = Object.keys(FIELDS[params.station]);
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
	const series = Object.values(FIELDS[params.station]).filter(f => f !== 'time');
	const axes = [
		{ scale: 'mb', size: 70 },
	];
	plot.init(axes);
	plot.series(series);
	if (data) plot.data(data);
}
const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('pressure-params', p)
});

export function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Local pressure sensors comparison<br>
Only supported for: ${SUPPORTED}`)
	]);
	tabs.fill('query', [
		tabs.input('station-only', (station) => {
			params.station = station;
			plotInit();
			query.params(params);
		}, { text: 'station:', list: SUPPORTED }),
		tabs.input('time', (from, to, force) => {
			params.from = from;
			params.to = to;
			query.params(params);
			if (force)
				query.fetch(params);
		}, { from: params.from, to: params.to }),
		query.el
	]);
}

export function load() {
	plotInit();
	query.fetch(params);
}

export function unload() {
	if (query)
		query.stop();
}

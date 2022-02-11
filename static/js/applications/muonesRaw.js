import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';

const FIELDS = {
	Moscow: {
		time: 'time',
		c0: {
			label: 'c1',
			scale: 'n',
			color: 'rgba(255,200,100,1)',
			nounit: true
		},
		c1: {
			label: 'c2',
			scale: 'n',
			color: 'rgba(255,150,100,1)',
			nounit: true
		},
		n_v: {
			label: 'n_v',
			scale: 'n',
			color: 'rgba(255,0,0,1)',
			nounit: true
		},
		pressure: {
			label: 'p',
			scale: 'mb',
			color: 'rgba(200,0,255,1)',
			precision: 1
		},
		temperature: {
			label: 't',
			scale: '°C',
			color: 'rgba(100,255,100,1)',
			precision: 1,
			show: false
		},
		temperature_ext: {
			label: 't_ext',
			scale: '°C',
			color: 'rgba(150,255,150,1)',
			precision: 1
		},
		voltage: {
			label: 'v',
			scale: 'v',
			color: 'rgba(100,40,100,1)',
			precision: 2,
			show: false
		},
	}
};
const SUPPORTED = Object.keys(FIELDS);
const URL = 'api/muones/raw';
const params = util.storage.getObject('muonesRaw-params') || {
	from: Math.floor(Date.now()/1000) - 86400*10 - 86400*7,
	to: Math.floor(Date.now()/1000) - 86400*10,
	station: 'Moscow',
	period: 3600
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
		{ scale: 'n' , nounit: true},
		{ scale: 'mb', side: 1, size: 70, show: true },
		{ scale: 'nd', nounit: true, show: false  },
		{ scale: '°C', show: false },
		{ scale: 'v', side: 1, size: 70, show: true, precision: 2  }
	];
	plot.init(axes);
	plot.series(series);
	if (data) plot.data(data);
}
const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('muonesRaw-params', p)
});

export function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Get raw data of local muones telescope.<br>
Only supported for: ${SUPPORTED}`)
	]);
	const periods = ['1 hour', '1 minute'];
	tabs.fill('query', [
		tabs.input('switch', per => {
			params.period = per.includes('minute') ? 60 : 3600;
			query.params(params);
		}, { options: params.period===60?periods.reverse():periods, text: 'period: ' }),
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
	query.fetch(params);
}

export function load() {
	plotInit(data);
}

export function unload() {
	if (query)
		query.stop();
}

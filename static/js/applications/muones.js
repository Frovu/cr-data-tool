import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';

const FIELDS = {
	time: 'time',
	source: {
		isChannel: true,
		label: 'source',
		scale: 'n',
		color: 'rgba(60,10,150,0.5)'
	},
	corrected_v: {
		isChannel: true,
		label: 'corrected_v',
		scale: 'n',
		color: 'rgba(255,100,60,0.8)'
	},
	corrected: {
		isChannel: true,
		label: 'corrected',
		scale: 'n',
		color: 'rgba(255,10,60,1)'
	},
	pressure: {
		label: 'pressure',
		scale: 'mb',
		color: 'rgba(200,0,200,0.6)',
		precision: 1,
		show: false
	},
	v_expected: {
		label: 'v_gsm',
		scale: '% ',
		color: 'rgba(0,255,200,0.6)',
		precision: 1,
		show: true
	},
	v_expected1: {
		label: 'v_gsm_isotropic',
		scale: '%',
		color: 'rgba(0,255,100,0.6)',
		precision: 1,
		show: false
	},
	T_m: {
		label: 'temperature',
		scale: 'K',
		color: 'rgba(255,155,50,1)',
		precision: 1,
		show: false
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
if (params.coefs === 'retain')
	params.coefs = 'recalc';
let coefsTmp = params.coefs;
let data = [];
let info;
let viewMode = 'counts';

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

function countsToVariation(data) {
	const newData = Object.assign([], data);
	for (const i of info.coef_v0 ? [1, 2, 3] : [1, 3]) {
		const avg = data[i].reduce((a,b) => (a+b)) / data[i].length;
		newData[i] = data[i].map(c => (c / avg - 1) * 100);
	}
	return newData;
}

function plotInit() {
	const axes = [
		{ scale: 'n' , nounit: true, show: viewMode === 'counts' },
		{ scale: '%' , side: viewMode === 'counts' ? 1 : 3, show: viewMode === 'variation' },
		{ scale: '% ' , side: 1, show: viewMode === 'counts' },
		{ scale: 'mb', side: 1, size: 70 },
		{ scale: 'K', side: 1 }
	];
	const cl = info && Math.floor(info.coef_per_length/86400);
	const c_pr = info && info.coef_pressure ? `c_pr=${info.coef_pressure.toFixed(4)} ` : '';
	const title = info && `${params.station}:${params.channel} ${c_pr}c_tm=${info.coef_temperature.toFixed(4)} c_v=${info.coef_v0.toFixed(4)};${info.coef_v1.toFixed(4)} cl=${cl}d`;
	plot.init(axes, true, null, null, title);
	const series = Object.values(FIELDS).filter(f => f !== 'time');
	for (const s of series) {
		if (s.isChannel) {
			s.scale = viewMode === 'counts' ? 'n' : '%';
			s.precision = viewMode === 'counts' ? 0 : 2;
			s.nounit = viewMode === 'counts';
		}
	}
	plot.series(series);
	if (data.length) plot.data(viewMode === 'counts' ? data : countsToVariation(data));
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
	const cleanBtn = tabs.input('query', () => {}, {
		url: `${URL}/clean`, text: 'clean', params: params, method: 'POST'
	});
	const despikeBtn = tabs.input('query', resp => {
		console.log(`despike done: ${resp.count} points`);
		despikeBtn.elem.innerHTML = `=${resp.count || NaN}`;
		query.fetch(params);
	}, {
		url: `${URL}/despike`, text: 'despike', params: params, method: 'POST'
	});
	const admin = document.createElement('details');
	admin.innerHTML = '<summary><u>Advanced</u> (Admin)</summary><p>';
	const retainCoefs = tabs.input('checkbox', val => {
		params.coefs = val ? 'retain' : coefsTmp;
		query.params(params);
	}, { text: ' write coefs' });
	admin.append(retainCoefs, document.createElement('p'), cleanBtn.elem, despikeBtn.elem);
	// const periods = ['1 hour', '1 minute'];
	tabs.fill('query', [
		stations ?
			tabs.input('station-channel', (station, channel) => {
				params.station = station;
				params.channel = channel;
				cleanBtn.setParams(params);
				query.params(params);
			}, { text: 'station:', list: stations, station: params.station, channel: params.channel }) :
			tabs.text(sText),
		// tabs.input('switch', per => {
		// 	params.period = per.includes('minute') ? 60 : 3600;
		// 	query.params(params);
		// }, { options: params.period===60?periods.reverse():periods, text: 'period: ' }),
		tabs.input('time', (from, to, force) => {
			params.from = from;
			params.to = to;
			cleanBtn.setParams(params);
			query.params(params);
			if (force)
				query.fetch(params);
		}, { from: params.from, to: params.to }),
		tabs.input('switch', opt => {
			viewMode = opt;
			plotInit(data);
		}, { options: ['variation', 'counts'], active: viewMode, text: 'view: ' }),
		tabs.input('switch', opt => {
			coefsTmp = opt;
			params.coefs = opt;
			query.params(params);
		}, { options: ['saved', 'recalc'], active: params.coefs, text: 'coefs: ' }),
		admin,
		query.el
	]);
	tabs.fill('tools', [
		// TODO:
		// rename stations to expiriments
		// despike on all channels
		// manual despike for all channels
		// continue to plot temp coefs
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

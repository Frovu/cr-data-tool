import * as tabs from '../lib/tabsUtil.js';
import * as util from '../lib/util.js';
import * as plot from '../plot.js';

const FIELDS = {
	time: 'time',
	corrected: {
		isChannel: true,
		label: 'corrected',
		scale: 'n',
		color: 'rgba(255,10,60,1)'
	},
	v_expected: {
		label: 'v_gsm',
		scale: '%',
		color: 'rgba(0,255,200,0.6)',
		precision: 1
	},
	source: {
		isChannel: true,
		label: 'source',
		scale: 'n',
		color: 'rgba(60,10,150,0.5)',
		show: false
	},
	T_m: {
		label: 'temperature',
		scale: 'K',
		color: 'rgba(255,155,50,1)',
		precision: 1,
		show: false
	},
	pressure: {
		label: 'pressure',
		scale: 'mb',
		color: 'rgba(200,0,200,0.6)',
		precision: 1,
		show: false
	},
	v_expected1: {
		label: 'v_gsm_isotropic',
		scale: '% ',
		color: 'rgba(0,255,100,0.6)',
		precision: 1,
		show: false
	},
	corrected_v: {
		isChannel: true,
		label: 'corrected_v',
		scale: 'n',
		color: 'rgba(255,100,60,0.8)',
		show: false
	},
	T_eff: {
		label: 'temperature',
		scale: 'K',
		color: 'rgba(255,155,50,1)',
		precision: 1,
		show: false
	},
};
const URL = 'api/muones';
const params = util.storage.getObject('muones-params') || {
	from: new Date('2021-10-20').getTime() / 1000,
	to: new Date('2021-12-20').getTime() / 1000,
	station: 'Moscow-pioneer',
	coefs: 'recalc',
	channel: 'V',
	period: 3600
};
if (params.coefs === 'retain')
	params.coefs = 'recalc';
let coefsTmp = params.coefs;
let data = [];
let info, commitBtn, resetTools;
let viewMode = 'variation';
let allChannels = false;
let editMode = false;
let inTransaction = false;

function receiveData(resp) {
	const rows = resp.data, len = resp.data.length;
	exprt.setData(resp.data, resp.fields);
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
	for (const [i, field] of Object.values(FIELDS).entries()) {
		if (!field.isChannel) continue;
		const avg = data[i].reduce((a,b) => (a+b)) / data[i].length;
		newData[i] = data[i].map(c => (c / avg - 1) * 100);
	}
	return newData;
}

async function plotClick(idx) {
	if (!editMode) return;
	const tstmp = data[0][idx];
	console.log('removing point at', new Date(tstmp*1000).toISOString());
	const res = await fetch(`${URL}/fix`, {
		headers: {'Content-Type': 'application/x-www-form-urlencoded'},
		body: `station=${encodeURIComponent(params.station)}&channel=${allChannels?'all':params.channel}&period=${params.period}&timestamp=${tstmp}`,
		method: 'POST'
	});
	if (res.status == 200) {
		const body = await res.json();
		console.log(body.count ? 'done' : 'nothing changed');
		for (let i=1; i<data.length; ++i)
			data[i][idx] = null;
		inTransaction = true;
		plot.data(viewMode === 'counts' ? data : countsToVariation(data), false);
		commitBtn.elem.classList.add('active');
	} else {
		console.log('failed:', res.status);
	}
}

function plotInit() {
	const axes = [
		{ scale: 'n' , nounit: true, show: viewMode === 'counts' },
		{ scale: '%' , side: viewMode === 'counts' ? 1 : 3 },
		{ scale: '% ' , side: 1 },
		{ scale: 'mb', side: 1, size: 70 },
		{ scale: 'K', side: 1 }
	];
	const cl = info && Math.floor(info.coef_per_length/86400);
	const c_pr = info && info.coef_pressure ? `c_pr=${info.coef_pressure.toFixed(4)} ` : '';
	const title = info && `${params.station}:${params.channel} ${c_pr}c_tm=${info.coef_temperature.toFixed(4)} c_v=${info.coef_v0.toFixed(4)};${info.coef_v1.toFixed(4)} cl=${cl}d`;
	plot.init(axes, true, null, null, title, plotClick);
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


const exprt = tabs.exportTab(URL, params);
const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => {
		util.storage.setObject('muones-params', p);
		exprt.setParams(p);
	}
});

async function fetchStations() {
	const resp = await fetch(URL + '/stations').catch(()=>{});
	if (!resp || resp.status !== 200) return null;
	return (await resp.json()).list;
}

export async function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Temperature corrected data of muon telescopes.<br>
Correction is performed via mass-average temperature method. <a href="https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html">NCEP/NCAR</a> and <a href="https://nomads.ncep.noaa.gov/txt_descriptions/GFS_doc.shtml">GFS</a> are used as data source.<br>
If you by some ocasion have a muon telescope and want to setup easy correction of your data, please <a href="mailto:izmiran.crdt@gmail.com">contact us</a>.
`)
	]);
	const stations = await fetchStations() || [];
	const sText = stations ? stations.join() : 'Stations failed to load, refresh tab please.';
	const admin = document.createElement('details');
	admin.innerHTML = '<summary><u>Advanced</u> (Admin)</summary><p>';
	const retainCoefs = tabs.input('checkbox', val => {
		params.coefs = val ? 'retain' : coefsTmp;
		query.params(params);
	}, { text: 'write coefs' });
	admin.append(retainCoefs);
	// const periods = ['1 hour', '1 minute'];
	tabs.fill('query', [
		stations ?
			tabs.input('station-channel', (station, channel) => {
				params.station = station;
				params.channel = channel;
				resetTools();
				query.params(params);
			}, { text: 'experiment:', list: stations, station: params.station, channel: params.channel }) :
			tabs.text(sText),
		tabs.input('time', (from, to, force) => {
			params.from = from;
			params.to = to;
			query.params(params);
			if (force)
				query.fetch(params);
		}, { from: params.from, to: params.to }),
		tabs.input('switch', opt => {
			params.tmode = opt;
			query.params(params);
		}, { options: ['T_m', 'T_eff'], active: params.tmode, text: 'temp mode: ' }),
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

	const allChannelsBox = tabs.input('checkbox', val => {
		allChannels = val;
	}, { text: 'all channels' });
	const cleanBtn = tabs.input('query', () => {}, {
		url: `${URL}/clean`, text: 'clean', method: 'POST',
		params: () => new Object({
			channel: allChannels ? 'all' : params.channel,
			station: params.station,
			period: params.period
		})
	});
	const despikeBtn = tabs.input('query', resp => {
		console.log(`despike done: ${resp.count} points`);
		despikeBtn.elem.innerHTML = `=${resp.count || NaN}`;
		inTransaction = true;
		commitBtn.elem.classList.add('active');
		query.fetch(params);
	}, {
		url: `${URL}/despike`, text: 'auto despike', method: 'POST',
		params: () => new Object({
			channel: allChannels ? 'all' : params.channel,
			station: params.station,
			period: params.period
		})
	});
	commitBtn = tabs.input('query', () => {
		if (inTransaction) {
			inTransaction = false;
			query.fetch(params);
		}
		editMode = false;
		editSwitch.children[0].innerHTML = 'view';
		editSwitch.children[0].classList.remove('invalid');
		commitBtn.elem.classList.remove('active');
	}, {
		url: `${URL}/commit`, text: 'commit', method: 'POST'
	});
	const rollbackBtn = tabs.input('query', () => {
		if (inTransaction) {
			inTransaction = false;
			query.fetch(params);
		}
		editMode = false;
		editSwitch.children[0].innerHTML = 'view';
		editSwitch.children[0].classList.remove('invalid');
		commitBtn.elem.classList.remove('active');
	}, {
		url: `${URL}/commit`, text: 'rollback', method: 'POST', params: { rollback: 'rollback'}
	});
	const editSwitch = tabs.input('switch', opt => {
		editMode = opt === 'edit';
		if (!editMode) {
			commitBtn.elem.classList.remove('active');
			if (inTransaction)
				rollbackBtn.fetch();
		}
		editSwitch.children[0].classList[editMode?'add':'remove']('invalid');
	}, { options: ['view', 'edit'], active: editMode, text: 'mode: ' });
	const div = document.createElement('div');
	div.style.textAlign = 'right';
	div.append(commitBtn.elem, rollbackBtn.elem);
	tabs.fill('tools', [
		cleanBtn.elem,
		despikeBtn.elem,
		document.createElement('p'),
		allChannelsBox,
		document.createElement('p'),
		document.createElement('p'),
		editSwitch,
		div
	]);

	resetTools = () => {
		if (inTransaction)
			rollbackBtn.fetch();
		inTransaction = false;
		editMode = false;
		editSwitch.children[0].innerHTML = 'view';
		editSwitch.children[0].classList.remove('invalid');
		commitBtn.elem.classList.remove('active');
		allChannelsBox.firstChild.checked = false;
		allChannels = false;
	};
	tabs.fill('export', [exprt.el]);

	query.fetch(params);
}

export function load() {
	plotInit(data);
}

export function unload() {
	if (query)
		query.stop();
}

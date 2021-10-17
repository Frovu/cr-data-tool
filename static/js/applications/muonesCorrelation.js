import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';

const URL = 'api/muones/correlation';
const params = util.storage.getObject('muonesCorr-params') || {
	from: Math.floor(Date.now()/1000) - 86400*10 - 86400*90,
	to: Math.floor(Date.now()/1000) - 86400*10,
	station: 'Moscow',
	period: 60,
	against: 'pressure'
};
const SCALE = {
	pressure: 'mb',
	Tm: 'K'
};
let data;

function receiveData(resp) {
	const rows = resp.data, len = resp.data.length;
	const nidx = resp.fields.findIndex(f => f !== params.against);
	const aidx = resp.fields.indexOf(params.against);
	data = [Array(len), Array(len)];
	let sum = 0, count=0;
	for (let i = 0; i < len; ++i) {
		const n = rows[i][nidx];
		if (n) {
			++count;
			sum += n;
		}
	}
	const avg = sum / count;
	const filter = Math.floor(avg - avg/4);
	let filtered = 0;
	for (let i = 0; i < len; ++i) {
		const n = rows[i][nidx];
		if (n < filter) {
			++filtered;
			continue;
		}
		data[0][i] = rows[i][aidx];
		data[1][i] = n;
	}
	data = [null, data];
	console.warn(`avg=${avg.toFixed()} filtered (<${filter}) = ${filtered}`);
	plotInit(data);
}

function plotInit(data) {
	if (!data) return;
	plot.initCorr(`N(${params.against})`, params.period===60?2:4, data);
}

async function fetchStations() {
	const resp = await fetch('api/muones/stations').catch(()=>{});
	if (!resp || resp.status !== 200) return null;
	return (await resp.json()).list;
}

const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('muonesCorr-params', p)
});

export async function initTabs() {
	const stations = (await fetchStations() || []).map(s => s.name);
	const sText = stations ? stations.join() : 'Stations failed to load, refresh tab please.';
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Plot correlations of muones telescopes data.<br>
Supported only for ${sText}`)
	]);
	const periods = ['1 hour', '1 minute'];
	tabs.fill('query', [
		tabs.input('switch', per => {
			params.period = per.includes('minute') ? 60 : 3600;
			query.params(params);
		}, { options: params.period===60?periods.reverse():periods, text: 'period: ' }),
		stations ?
			tabs.input('station-only', (station) => {
				params.station = station;
				plotInit();
				query.params(params);
			}, { text: 'station:', list: stations }) :
			tabs.text(sText),
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
		query.stop();
}

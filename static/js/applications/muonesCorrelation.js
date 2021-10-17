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
	// const rows = resp.data, len = resp.data.length;
	// const fields = Object.keys(FIELDS[params.station]);
	// const idx = Array(fields.length);
	// resp.fields.forEach((field, i) => {
	// 	const index = fields.indexOf(field);
	// 	if (index >= 0)
	// 		idx[index] = i;
	// });
	// data = fields.map(() => Array(len));
	// for (let i = 0; i < len; ++i) {
	// 	for (let j = 0; j < fields.length; ++j) {
	// 		data[j][i] = rows[i][idx[j]];
	// 	}
	// }
	// plot.data(data);
}

function plotInit() {
	const agScale = SCALE[params.against];
	plot.init([
		{ scale: 'n', side: 3, size: 70, nounit: true },
		{ scale: agScale, side: 2, space: 70 }
	], false, {
		// n: {
		// 	range: [0, 1000],
		// 	time: false,
		// 	dir: -1,
		// 	ori: 1
		// },
		// [temperatureUnit]: {
		// 	dir: 1,
		// 	ori: 0
		// }
	}, [
		{
			scale: 'mb',
			label: 'Height',
			color: null
		}, {
			scale: agScale,
			label: params.against,
			// color: 'red',
			// width: 3,
			// precision: 1,
		}
	]);
	if (data) plot.data(data);
}

async function fetchStations() {
	const resp = await fetch('api/muones/stations').catch(()=>{});
	if (!resp || resp.status !== 200) return null;
	return (await resp.json()).list;
}

const query = util.constructQueryManager(URL, {
	data: receiveData,
	params: p => util.storage.setObject('muonesRaw-params', p)
});

export async function initTabs() {
	const stations = await fetchStations();
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

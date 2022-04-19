import * as tabs from '../lib/tabsUtil.js';
import * as util from '../lib/util.js';
import * as plot from '../plot.js';

const URL = 'api/muones/correlation';
const params = util.storage.getObject('muonesCorr-params') || {
	from: Math.floor(Date.now()/1000) - 86400*5 - 86400*365,
	to: Math.floor(Date.now()/1000) - 86400*5,
	station: 'Apatity',
	period: 3600,
	channel: 'V',
	against: 'pressure'
};
let data;
let info = {};

function receiveData(resp) {
	const dt = resp.data;
	data = [null, [dt.x, dt.y], [dt.rx, dt.ry]];
	info.slope = dt.slope;
	info.error = dt.error;
	plotInit(data);
}

function plotInit(data) {
	if (!data) return;
	const title = `${params.station}:${params.channel} [${data[1][1].length} points], stderr=${info.error.toFixed(6)}`;
	const corr = `c=${info.slope.toFixed(6)}`;
	plot.initCorr(data, `v(${params.against})`, params.period===60?2:3, title, corr);
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
	const stations = await fetchStations() || [];
	const sText = stations ? stations.map(s => s.name).join(', ') : 'Stations failed to load, refresh tab please.';
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Plot correlations of muones telescopes data.<br>
Supported only for ${sText}`)
	]);
	const periods = ['hour', 'minute'];
	const against = ['pressure', 'T_m', 'T_eff'];
	tabs.fill('query', [
		stations ?
			tabs.input('station-channel', (station, channel) => {
				params.station = station;
				params.channel = channel;
				plotInit();
				query.params(params);
			}, { text: 'station:', list: stations, station: params.station, channel: params.channel }) :
			tabs.text(sText),
		tabs.input('switch', per => {
			params.period = per.includes('minute') ? 60 : 3600;
			query.params(params);
		}, { options: periods, text: 'period: ', active: params.period == 3600 ? 'hour' : 'minute'}),
		tabs.input('switch', ag => {
			params.against = ag;
			query.params(params);
		}, { options: against, text: 'against: ', active: params.against }),
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

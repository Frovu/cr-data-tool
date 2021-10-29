import * as tabs from '../tabsUtil.js';
import * as util from '../util.js';
import * as plot from '../plot.js';

const URL = 'api/muones/correlation';
const params = util.storage.getObject('muonesCorr-params') || {
	from: Math.floor(Date.now()/1000) - 86400*5 - 86400*365,
	to: Math.floor(Date.now()/1000) - 86400*5,
	station: 'Moscow',
	period: 3600,
	against: 'pressure'
};
let data;
let r;

function receiveData(resp) {
	const dt = resp.data;
	data = [null, [dt.x, dt.y], [dt.rx, dt.ry]];
	r = dt.r;
	plotInit(data);
}

function plotInit(data) {
	if (!data) return;
	plot.initCorr(data, `N(${params.against})`, params.period===60?2:4, `r=${r.toFixed(4)}`);
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
	const against = ['pressure', 'Tm'];
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
		tabs.input('switch', ag => {
			params.against = ag;
			query.params(params);
		}, { options: params.against!==against[0]?against.reverse():against, text: 'against: ' }),
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

import * as tabs from '../tabsUtil.js';
import * as plot from '../plot.js';

const params = {
	from: Math.floor(Date.now()/1000) - 86400,
	to: Math.floor(Date.now()/1000) + 3600,
	period: '1 hour'
};
let data;
const SERIES = {
	get_result: {
		label: 'result',
		scale: 'n',
		color: 'rgb(0,255,255)',
		nounit: true
	},
	query_accepted: {
		label: 'calculation',
		scale: 'n',
		color: 'rgb(255,10,100)',
		nounit: true
	}
};

function receiveData(resp) {
	const rows = resp.data, len = resp.data.length;
	const fields = ['time'].concat(Object.keys(SERIES));
	const idx = Array(fields.length);
	resp.fields.forEach((field, i) => {
		const index = fields.indexOf(field);
		if (index >= 0)
			idx[index] = i;
	});
	data = fields.map(() => Array(len));
	console.log(idx)
	for (let i = 0; i < len; ++i) {
		for (let j = 0; j < fields.length; ++j) {
			data[j][i] = rows[i][idx[j]];
		}
	}
	console.log(data)
}

function drawPlot(data) {
	plot.init([{ scale: 'n' , nounit: true}]);
	plot.series(Object.values(SERIES));
	console.log(data)
	if (data) plot.data(data);
}

export function initTabs() {
	tabs.fill('app', [
		tabs.text('<h4>Description</h4> Admin tool + infographics.')
	]);
	const statsQuery = tabs.input('query', resp => {
		receiveData(resp);
		drawPlot(data);
	}, { url: 'api/admin/stats', params });
	const periodInput = tabs.input('text', per => {
		params.period = per;
		statsQuery.setParams(params);
	}, { value: params.period, label: 'Interval:' });
	periodInput.append(statsQuery.elem);
	tabs.fill('query', [
		tabs.input('time', (from, to) => {
			params.from = from;
			params.to = to;
		}, { from: params.from, to: params.to }),
		periodInput,
	]);
	statsQuery.fetch(params);
}

export function load() {
	drawPlot(data);
}

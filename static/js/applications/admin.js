import * as tabs from '../tabsUtil.js';
import * as plot from '../plot.js';

const params = {
	from: Math.floor(Date.now()/1000) - 86400*7,
	to: Math.floor(Date.now()/1000) + 86400,
	period: '1 hour'
};
let data;

function drawPlot() {

}

export function initTabs() {
	tabs.fill('app', [
		tabs.text('<h4>Description</h4> Admin tool + infographics.')
	]);
	const statsQuery = tabs.input('query', result => {
		data = result;
		drawPlot();
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

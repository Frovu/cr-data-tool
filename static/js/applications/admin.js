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
	for (let i = 0; i < len; ++i) {
		for (let j = 0; j < fields.length; ++j) {
			data[j][i] = rows[i][idx[j]];
		}
	}
}

function drawPlot(data) {
	plot.init([{ scale: 'n' , nounit: true}]);
	plot.series(Object.values(SERIES));
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

	const userList = document.createElement('details');
	userList.innerHTML = '<summary>Users list</summary>';
	fetch('api/admin/listUsers').then(async res => {
		if (res.status == 200) {
			const data = await res.json();
			userList.innerHTML += '<p>'+data.list.map(u => `<i>${u}</i>`).join(', ')+'</p>';
		} else {
			userList.innerHTML = 'Failed to load';
		}
	});
	const userOpts = {};
	const userPerms = document.createElement('div');
	const queryUser = tabs.input('query', resp => {
		userPerms.innerHTML = '<h4>Permissions</h4>';
		userPerms.innerHTML = Object.keys(resp).map(k => `<p>${k}: <i>${resp[k].join()}</i></p>`).join('\n');
	}, { url: 'api/admin/user', options: userOpts });
	const usernameInp = tabs.input('text', uname => {
		userOpts.username = uname;
		queryUser.setParams(userOpts);
	}, { label: 'Username:' });
	usernameInp.append(queryUser.elem);
	tabs.fill('tools', [
		userList,
		usernameInp,
		userPerms
	]);
	statsQuery.fetch(params);
}

export function load() {
	drawPlot(data);
}

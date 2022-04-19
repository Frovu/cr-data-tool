import * as tabs from '../lib/tabsUtil.js';
import * as plot from '../plot.js';

const params = {
	from: (Math.floor(Date.now()/1000/3600)-1)*3600-86400,
	to: Math.floor(Date.now()/1000),
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

	const editPerms = document.createElement('details');
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
	const permOpts = {};
	const userPerms = document.createElement('p');
	const queryUser = tabs.input('query', resp => {
		editPerms.hidden = null;
		userPerms.innerHTML = '<h4>Permissions</h4>';
		userPerms.innerHTML += Object.keys(resp).map(k => `<p>${k}: <i>${resp[k].join()}</i></p>`).join('\n');
	}, { url: 'api/admin/user', text: 'Fetch' });
	const usernameInp = tabs.input('text', uname => {
		userOpts.username = uname;
		permOpts.username = uname;
		queryUser.setParams(userOpts);
	}, { label: 'Username:' });
	usernameInp.append(queryUser.elem);

	editPerms.innerHTML = '<summary><u>Edit permissions</u></summary>';
	editPerms.open = true;
	editPerms.hidden = 'true';
	const permAdd = tabs.input('query', () => {
		queryUser.fetch();
	}, { url: 'api/admin/permissions/add', text: 'Allow' });
	const permRemove = tabs.input('query', () => {
		queryUser.fetch();
	}, { url: 'api/admin/permissions/remove', text: 'Forbid' });
	const permFlagInp = tabs.input('text', val => {
		permOpts.flag = val;
		permAdd.setParams(permOpts);
		permRemove.setParams(permOpts);
	}, { label: '&nbsp;&nbsp;Flag:', placeholder: 'USE_APPLICATION' });
	const permTargetInp = tabs.input('text', val => {
		permOpts.target = val;
		permAdd.setParams(permOpts);
		permRemove.setParams(permOpts);
	}, { label: 'Target:', placeholder: 'muon' });
	editPerms.append(document.createElement('p'), permFlagInp, permAdd.elem,
		document.createElement('p'), permTargetInp, permRemove.elem);

	tabs.fill('tools', [
		userList,
		document.createElement('p'),
		usernameInp,
		document.createElement('p'),
		editPerms,
		userPerms
	]);
	statsQuery.fetch(params);
}

export function load() {
	drawPlot(data);
}

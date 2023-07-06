import * as temperature from './applications/temperature.js';
import * as tempHeight from './applications/tempHeight.js';
import * as circles from './applications/circles.js';
import * as muon from './applications/muones.js';
import * as muonRaw from './applications/muonesRaw.js';
import * as muonCorr from './applications/muonesCorrelation.js';
import * as pressure from './applications/pressure.js';
import * as admin from './applications/admin.js';
import * as gflux from './applications/gflux.js';

const applications = {
	temperature,
	tempHeight,
	circles,
	muon,
	muonRaw,
	muonCorr,
	pressure,
	gflux,
	admin,
};
const hierarchy = {
	muon: ['muon', 'muonRaw', 'muonCorr', 'pressure'],
	temperature: ['temperature', 'tempHeight', 'gflux'],
	neutron: ['circles']
};
const publicApps = ['muon', 'neutron', 'temperature'];

const DEFAULT = 'muon';
const DONT_SAVE = ['info-tab', 'graph-tab', 'result-tab'];
const tabsCache = {};
const graphsCache = {};

let allowed = [DEFAULT];
let active;
const selects = [];

export async function swithApp(nextApp) {
	const tabs = document.getElementsByClassName('tab');
	const graphTab = document.getElementById('graph-tab');
	if (active) { // save app's tabs to cache
		const app = applications[active];
		if (!tabsCache[active]) tabsCache[active] = {};
		if (app.unload) app.unload();
		graphsCache[active] = graphTab.classList.contains('active');
		for (const tab of tabs) {
			if (DONT_SAVE.includes(tab.id)) continue;
			tabsCache[active][tab.id] = tab;
			const newTab = tab.cloneNode(true);
			newTab.innerHTML = '';
			document.body.replaceChild(newTab, tab);
		}
	}
	if (tabsCache[nextApp]) { // restore app's tabs from cache
		for (const tab of tabs) {
			if (DONT_SAVE.includes(tab.id)) continue;
			document.body.replaceChild(tabsCache[nextApp][tab.id], tab);
		}
		const graphBtn = document.getElementById('graph-btn');
		graphTab.classList[graphsCache[nextApp] ? 'add' : 'remove']('active');
		graphBtn.checked = graphsCache[nextApp];
	} else {
		for (const tab of tabs) {
			if (DONT_SAVE.includes(tab.id)) continue;
			tab.innerHTML = '';
		}
		const apptab = document.getElementById('app-tab');
		apptab.innerHTML = '<label for="app">Select application:&nbsp;</label>';
		const select = document.createElement('select');
		for (const app in applications) {
			const opt = document.createElement('option');
			opt.value = app;
			opt.innerHTML = app.charAt(0).toUpperCase() + app.slice(1);
			if (app === nextApp) opt.selected = 'selected';
			select.append(opt);
			opt.hidden = allowed.includes(app) ? null : 'true';
		}
		select.onchange = e => {
			e.preventDefault();
			const prev = active;
			swithApp(select.value);
			if (prev) select.value = prev;
		};
		selects.push(select);
		apptab.append(select);
		await applications[nextApp].initTabs();
	}
	for (const tab of tabs) {
		const button = document.getElementById(`${tab.id.split('-')[0]}-btn`);
		if (!button) continue;
		button.disabled = !tab.innerHTML;
		if (button.disabled)
			tab.classList.remove('active');
		if (tab.classList.contains('active'))
			button.checked = true;
		else
			button.checked = false;
	}
	if (applications[nextApp].load) applications[nextApp].load();
	active = nextApp;
	window.localStorage.setItem('application', active);
}

export async function init() {
	const savedApp = window.localStorage.getItem('application');
	await swithApp(applications[savedApp] ? savedApp : DEFAULT);
}

export function updateView(permissions) {
	const perm = permissions && permissions.USE_APPLICATION ? (permissions.USE_APPLICATION.includes('OVERRIDE') ?
		Object.keys(hierarchy) :  permissions.USE_APPLICATION) : [];
	allowed = [].concat.apply([], perm.concat(publicApps).map(h => hierarchy[h.toLowerCase()]));
	if (permissions && permissions.ADMIN) allowed.push('admin');
	for (const sel of selects) {
		for (const opt of sel.children) {
			opt.hidden = allowed.includes(opt.value) ? null : 'true';
			if (!allowed.includes(opt.value) && opt.selected)
				opt.selected = null;
		}
	}
	if (!allowed.includes(active))
		swithApp(DEFAULT);
}

window.onkeydown = e => {
	if (e.keyCode === 9) { // Tab
		e.preventDefault();
		const cached = Object.keys(tabsCache);
		if (!cached.length) return;
		const nextId = cached.indexOf(active) + 1;
		const restore = cached[nextId < cached.length ? nextId : 0];
		swithApp(restore);
	}
};
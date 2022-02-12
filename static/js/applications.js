import * as temperature from './applications/temperature.js';
import * as tempHeight from './applications/tempHeight.js';
import * as muones from './applications/muones.js';
import * as muonesRaw from './applications/muonesRaw.js';
import * as muonesCorr from './applications/muonesCorrelation.js';
import * as pressure from './applications/pressure.js';
import * as admin from './applications/admin.js';

const applications = {
	temperature,
	tempHeight,
	muones,
	muonesRaw,
	muonesCorr,
	pressure,
	admin
};
const hierarchy = {
	muon: ['muones', 'muonesRaw', 'muonesCorr', 'pressure'],
	temperature: ['temperature', 'tempHeight'],
};
const publicApps = ['temperature'];

const DEFAULT = 'temperature';
const tabsCache = {};

let allowed = [DEFAULT];
let active;
const selects = [];

export function swithApp(nextApp) {
	const tabs = document.getElementsByClassName('tab');
	if (active) { // save app's tabs to cache
		const app = applications[active];
		if (!tabsCache[active]) tabsCache[active] = {};
		if (app.unload) app.unload();
		for (const tab of tabs) {
			if (tab.id.startsWith('info')) continue;
			tabsCache[active][tab.id] = tab;
			const newTab = tab.cloneNode(true);
			newTab.innerHTML = '';
			document.body.replaceChild(newTab, tab);
		}
	}
	if (tabsCache[nextApp]) { // restore app's tabs from cache
		for (const tab of tabs) {
			if (tab.id.startsWith('info')) continue;
			document.body.replaceChild(tabsCache[nextApp][tab.id], tab);
		}
	} else {
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
		applications[nextApp].initTabs();
	}
	for (const tab of tabs) {
		const button = document.getElementById(`${tab.id.split('-')[0]}-btn`);
		button.disabled = !tab.innerHTML && !tab.id.startsWith('query');
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

export function init() {
	const savedApp = window.localStorage.getItem('application');
	swithApp(savedApp || DEFAULT);
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

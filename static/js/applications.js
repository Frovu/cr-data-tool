import * as temperature from './applications/temperature.js';
import * as tempHeight from './applications/tempHeight.js';
import * as muonesRaw from './applications/muonesRaw.js';

const applications = {
	temperature,
	tempHeight,
	muonesRaw
};

const tabsCache = {};

let active;
const selects = [];

export function swithApp(nextApp) {
	const tabs = document.getElementsByClassName('tab');
	if (active) { // save app's tabs to cache
		const app = applications[active];
		if (!tabsCache[active]) tabsCache[active] = {};
		if (app.unload) app.unload();
		for (const tab of tabs) {
			tabsCache[active][tab.id] = tab;
			const newTab = tab.cloneNode(true);
			newTab.innerHTML = '';
			document.body.replaceChild(newTab, tab);
		}
	}
	if (tabsCache[nextApp]) { // restore app's tabs from cache
		for (const tab of tabs) {
			// console.log(tabsCache[nextApp][tab.id])
			document.body.replaceChild(tabsCache[nextApp][tab.id], tab);
		}
	} else {
		const apptab = document.getElementById('app-tab');
		apptab.innerHTML = '<label for="app">Select application:</label>';
		const select = document.createElement('select');
		for (const app in applications) {
			const opt = document.createElement('option');
			opt.value = app;
			opt.innerHTML = app.charAt(0).toUpperCase() + app.slice(1);
			if (app === nextApp) opt.selected = 'selected';
			select.append(opt);
		}
		select.onchange = () => {
			swithApp(select.value);
			selects.forEach(sel => sel.value = select.value);
		};
		selects.push(select);
		apptab.append(select);
		applications[nextApp].initTabs();
	}
	if (applications[nextApp].load) applications[nextApp].load();
	active = nextApp;
	window.localStorage.setItem('application', active);
}

export function init() {
	const savedApp = window.localStorage.getItem('application');
	swithApp(savedApp || 'temperature');
}

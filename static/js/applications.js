import * as temperature from './applications/temperature.js';
import * as tempHeight from './applications/tempHeight.js';

const applications = {
	temperature,
	tempHeight
};

const tabsCache = {};

let active;
let select;

export async function swithApp(nextApp) {
	const tabs = document.getElementsByClassName('tab');
	if (active) { // save app's tabs to cache
		const app = applications[active];
		if (!tabsCache[active]) tabsCache[active] = {};
		if (app.unload) app.unload();
		for (const tab of tabs) {
			tabsCache[active][tab.id] = tab.cloneNode(true);
		}
	}
	if (tabsCache[nextApp]) { // restore app's tabs from cache
		for (const tab of tabs) {
			document.body.replaceChild(tab, tabsCache[nextApp][tab.id]);
		}
	} else {
		const apptab = document.getElementById('app-tab');
		apptab.innerHTML = '<label for="app">Select application:</label>';
		if (!select) {
			select = document.createElement('select');
			for (const app in applications) {
				const opt = document.createElement('option');
				opt.value = app;
				opt.innerHTML = app.charAt(0).toUpperCase() + app.slice(1);
				select.append(opt);
			}
			select.onchange = () => swithApp(select.value);
		}
		apptab.append(select);
		applications[nextApp].initTabs();
	}
	if (applications[nextApp].load) applications[nextApp].load();
	active = nextApp;
}

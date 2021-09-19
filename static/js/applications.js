import * as temperature from './applications/temperature.js';

const applications = {
	temperature
};

const tabsCache = {};

let active;

export async function swithApp(nextApp) {
	const tabs = document.getElementsByClassName('tab');
	if (active) { // save app's tabs to cache
		const app = applications[active];
		if (!tabsCache[active]) tabsCache[active] = {};
		if (app.unload) app.unload();
		for (const tab of tabs) {
			tabsCache[active][tab.id] = tab.cloneNode(true);
			tab.innerHTML = '';
		}
	}
	if (tabsCache[nextApp]) { // restore app's tabs from cache
		for (const tab of tabs) {
			document.body.replaceChild(tab, tabsCache[nextApp][tab.id]);
		}
	} else {
		applications[nextApp].initTabs();
	}
	if (applications[nextApp].load) applications[nextApp].load();
	active = nextApp;
}

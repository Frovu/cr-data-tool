import * as applications from './applications.js';

const tabs = [
	'info',
	'app',
	'query',
	'tools',
	'view',
	'export',
	'graph'
];
let activeTab = 'app';

function showTab(tab) {
	const active = document.getElementById(`${activeTab}-tab`);
	active.classList.remove('active');
	const el = document.getElementById(`${tab}-tab`);
	el.classList.add('active');
	if (activeTab === 'graph' || tab === 'graph')
		window.dispatchEvent(new Event('resize')); // make sure to redraw plot
	activeTab = tab;
}

window.onload = () => {
	const theme = window.localStorage.getItem('main-theme') || 'default';
	const themeSelect = document.getElementById('theme-select');
	for (const opt of themeSelect.children) {
		opt.selected = opt.value === theme ? 'selected' : null;
	}
	themeSelect.onchange = () => {
		const newTheme = themeSelect.value;
		console.log('theme swithed: '+newTheme);
		document.documentElement.setAttribute('main-theme', newTheme);
		window.localStorage.setItem('main-theme', newTheme);
		applications.init();
	};
	for (const tab of tabs) {
		const el = document.getElementById(`${tab}-btn`);
		el.addEventListener('click', () => {
			showTab(tab);
		});
		if (el.checked) showTab(tab);
	}
	applications.init();
};

document.documentElement.setAttribute('main-theme', window.localStorage.getItem('main-theme') || 'default');

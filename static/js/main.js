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
	for (const tab of tabs) {
		const el = document.getElementById(`${tab}-btn`);
		el.addEventListener('click', () => {
			showTab(tab);
		});
		if (el.checked) showTab(tab);
	}
	applications.init();
};

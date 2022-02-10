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

async function login() {
	const loginInp = document.getElementById('uname');
	const pwdInp = document.getElementById('pwd');
	const uname = loginInp.value;
	const password = pwdInp.value;
	const error = document.getElementById('login-error');
	const res = await fetch('api/auth/login', {
		method: 'POST',
		body: `login=${uname}&password=${password}`
	});
	if (res.status === 200) {
		error.innerHTML = '';
		loginInp.classList.remove('invalid');
		pwdInp.classList.remove('invalid');
		const elIn = document.getElementById('logged-in');
		const elOut = document.getElementById('logged-out');
		const unameEl = document.getElementById('username');
		unameEl.innerHTML = uname;
		elOut.hidden = 'true';
		elIn.hidden = null;
	} else if (res.status === 404) {
		loginInp.classList.add('invalid');
		error.innerHTML = 'User not found.';
	} else if (res.status === 401) {
		pwdInp.classList.add('invalid');
		error.innerHTML = 'Wrong password.';
	} else {
		error.innerHTML = 'Failed to login.';
		console.log(res);
	}
}

async function register() {

}

async function checkLogin() {
	const res = await fetch('api/auth/login');
	const body = await res.json();
	const uname = body && body.login;
	const elIn = document.getElementById('logged-in');
	const elOut = document.getElementById('logged-out');
	if (uname) {
		elOut.hidden = 'true';
		elIn.hidden = null;
		const unameEl = document.getElementById('username');
		unameEl.innerHTML = uname;
	} else {
		elOut.hidden = null;
		elIn.hidden = 'true';
	}
	return uname;
}

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

	const loggedIn = checkLogin();
	applications.updateView();
	const loginBtn = document.getElementById('login');
	const regtrBtn = document.getElementById('register');
	loginBtn.onclick = login;
	regtrBtn.onclick = register;

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

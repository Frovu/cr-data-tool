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
	const pwdShow = document.getElementById('repeat-input');
	pwdShow.hidden = 'true';
	const loginInp = document.getElementById('uname');
	const pwdInp = document.getElementById('pwd');
	const uname = loginInp.value;
	const password = pwdInp.value;
	const error = document.getElementById('login-error');
	const res = await fetch('api/auth/login', {
		headers: {'Content-Type': 'application/x-www-form-urlencoded'},
		method: 'POST',
		body: `login=${uname}&password=${password}`
	});
	if (res.status === 200) {
		const body = await res.json();
		error.innerHTML = '';
		loginInp.classList.remove('invalid');
		pwdInp.classList.remove('invalid');
		const elIn = document.getElementById('logged-in');
		const elOut = document.getElementById('logged-out');
		const unameEl = document.getElementById('username');
		unameEl.innerHTML = body.login;
		elOut.hidden = 'true';
		elIn.hidden = null;
		applications.updateView(body.permissions);
	} else if (res.status === 404) {
		loginInp.classList.add('invalid');
		error.innerHTML = 'User not found.';
	} else if (res.status === 401 || !password.length) {
		pwdInp.classList.add('invalid');
		error.innerHTML = 'Wrong password.';
	} else {
		error.innerHTML = 'Failed to login.';
		console.error(res);
	}
}

async function logout() {
	const res = await fetch('api/auth/logout');
	if (res.status === 200) {
		const elIn = document.getElementById('logged-in');
		const elOut = document.getElementById('logged-out');
		const unameEl = document.getElementById('username');
		unameEl.innerHTML = '';
		elOut.hidden = null;
		elIn.hidden = 'true';
		applications.updateView();
	}
}

async function register() {
	const loginInp = document.getElementById('uname');
	const pwdInp = document.getElementById('pwd');
	const pwdRepeat = document.getElementById('pwd-repeat');
	const error = document.getElementById('login-error');
	loginInp.classList.remove('invalid');
	pwdInp.classList.remove('invalid');
	pwdRepeat.classList.remove('invalid');
	const pwdShow = document.getElementById('repeat-input');
	pwdShow.hidden = null;
	const uname = loginInp.value;
	const password = pwdInp.value;
	if (!uname.includes('@')) {
		loginInp.classList.add('invalid');
		error.innerHTML = 'Doesn\t look like an email.';
		return;
	}
	if (password.length < 6) {
		pwdInp.classList.add('invalid');
		error.innerHTML = 'Password too short.';
		return;
	}
	if (password !== pwdRepeat.value) {
		pwdRepeat.classList.add('invalid');
		error.innerHTML = 'Passwords do not match.';
		return;
	}
	const res = await fetch('api/auth', {
		headers: {'Content-Type': 'application/x-www-form-urlencoded'},
		method: 'POST',
		body: `login=${uname}&password=${password}`
	});
	if (res.status === 200) {
		await login();
	} else if (res.status === 409) {
		loginInp.classList.add('invalid');
		error.innerHTML = 'User already exists.';
	} else {
		error.innerHTML = 'Failed to register.';
		console.error(res);
	}
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
	console.log(`Logged in as ${uname}, permissions are:`, body.permissions);
	return body;
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

	document.getElementById('login').onclick = login;
	document.getElementById('logout').onclick = logout;
	document.getElementById('register').onclick = register;

	for (const tab of tabs) {
		const el = document.getElementById(`${tab}-btn`);
		el.addEventListener('click', () => {
			showTab(tab);
		});
		if (el.checked) showTab(tab);
	}
	applications.init();

	checkLogin().then(r => applications.updateView(r.permissions));
};

document.documentElement.setAttribute('main-theme', window.localStorage.getItem('main-theme') || 'default');

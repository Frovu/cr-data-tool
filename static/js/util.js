// import * as tabsUtil from '../tabsUtil.js';
// export const tabs = tabsUtil;

const storageInterface = {
	get: window.localStorage.getItem,
	set: window.localStorage.setItem
};

export const storage = {
	...storageInterface,
	setObject: (key, obj) => storageInterface.set(key, JSON.stringify(obj)),
	getObject: (key) => {
		try {
			const item = storageInterface.get(key);
			return JSON.parse(item);
		} catch(e) {
			console.error('failed to parse from storage: '+key);
			return null;
		}
	}
};

function encodeParams(obj) {
	const keys = Object.keys(obj);
	return keys.length ? '?' + keys.map(k => `${k}=${obj[k]}`).join('&') : '';
}

export function constructQueryManager(url, callbacks) {
	let params, fetchInterval, fetchOngoing, paramsChanged;
	const el = document.createElement('button');
	el.classList.add('submit');
	el.innerHTML = 'Query data';
	const fetchOnce = async () => {
		const resp = await fetch(`${url}${encodeParams(params)}`).catch(()=>{});
		if (resp && resp.status === 200) {
			const body = await resp.json().catch(()=>{});
			console.log('resp:', body);
			if (body.status === 'ok') {
				el.innerHTML = 'Done!';
				return body;
			} else if (body.status === 'busy') {
				el.innerHTML = body.download ? `Downloading: ${(100*body.download).toFixed(0)} %` : 'Calculating...';
			// } else if (body.status === 'unknown') {
			} else if (body.status === 'accepted') {
				el.innerHTML = 'Accepted';
			} else {
				el.innerHTML = 'Error..';
			}
		} else {
			console.log('request failed', resp && resp.status);
			el.innerHTML = 'Failed';
			return null;
		}
	};
	const initFetch = async (p) => {
		if (p) params = p;
		if (!fetchOngoing && params) {
			el.classList.add('ongoing');
			el.innerHTML = 'Query...';
			el.classList.remove('active');
			fetchOngoing = true;
			paramsChanged = false;
			const data = await fetchOnce() || await new Promise(resolve => {
				fetchInterval = setInterval(() => {
					fetchOnce().then(ok => {
						if (typeof ok === 'undefined') return;
						resolve(ok);
						clearInterval(fetchInterval);
						fetchInterval = null;
					});
				}, 2000);
			});
			if (data && callbacks.data) callbacks.data(data);
			fetchOngoing = false;
			el.classList.remove('ongoing');
			if (paramsChanged) {
				setTimeout(() => {
					el.classList.add('active');
					el.innerHTML = 'Query data';
				}, 500);
			}
		}
	};
	el.addEventListener('click', () => initFetch());
	return {
		params: (p, force) => {
			if (force) {
				params = p;
				return initFetch(p);
			}
			if (params && Object.keys(p).every(k => params[k] === p[k])) {
				params = p;
				if (!fetchOngoing) {
					el.classList.add('active');
					el.innerHTML = 'Query data';
				} else {
					paramsChanged = true;
				}
			}
		},
		fetch: initFetch,
		stop: () => {
			clearInterval(fetchInterval);
			fetchInterval = null;
		},
		buttonEl: el
	};
}

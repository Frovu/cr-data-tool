const storageObject = window.localStorage;

export const storage = {
	set: (key, val) => storageObject.setItem(key, val),
	get: (key) => storageObject.getItem(key),
	setObject: (key, obj) => storageObject.setItem(key, JSON.stringify(obj)),
	getObject: (key) => {
		try {
			const item = storageObject.getItem(key);
			return item && JSON.parse(item);
		} catch(e) {
			console.error('failed to parse from storage: '+key);
			return null;
		}
	}
};

function encodeParams(obj) {
	const keys = Object.keys(obj);
	return keys.length ? '?' + keys.filter(k => obj[k] || obj[k] == 0).map(k => `${k}=${obj[k]}`).join('&') : '';
}

export function constructQueryManager(url, callbacks, progDetails=true, insistent=false) {
	let params, fetchParams, fetchInterval, fetchOngoing, paramsChanged;
	const div = document.createElement('div');
	div.classList.add('query');
	const progEl = progDetails && document.createElement('div');
	if (progDetails) progEl.classList.add('query-progress');
	const el = document.createElement('button');
	el.classList.add('submit');
	el.innerHTML = 'Query data';
	const fetchOnce = async () => {
		const resp = await fetch(`${url}${encodeParams(params)}`).catch(e=>{console.error(e);});
		const body = resp && resp.status === 200 && await resp.json().catch(e=>{console.error(e);});
		if (progEl) progEl.innerHTML = '';
		console.log('resp:', resp && resp.status, body);
		if (body) {
			if (body.status === 'ok') {
				el.innerHTML = 'Done!';
				return body;
			} else if (body.status === 'busy') {
				const prog = body.info && body.info.progress;
				const ic = prog && Object.values(prog).filter(v => v < 1);
				el.innerHTML = `Proceessing..${ic?(ic.length?(100*ic.reduce((a,b)=>a+b)/ic.length):100).toFixed(0)+'%':''}`;
				if (progEl && prog)
					progEl.innerHTML = Object.keys(prog).map(k=>`${k}: ${(100*prog[k]).toFixed(0)}%`).join('<br>');
			} else if (body.status === 'failed') {
				const reason = body.info && body.info.failed;
				el.innerHTML = 'Error';
				if (progDetails) progEl.innerHTML = `Failed: ${reason}`;
				return null;
			} else if (body.status === 'accepted') {
				el.innerHTML = 'Accepted';
			} else {
				el.innerHTML = 'Unknown Error';
				return null;
			}
		} else {
			console.log('request failed', resp && resp.status);
			el.innerHTML = 'Failed';
			return null;
		}
	};
	const initFetch = async (p) => {
		if (p)
			params = p;
		if (!fetchOngoing && params) {
			fetchParams = Object.assign({}, params);
			if (callbacks.params) callbacks.params(params);
			el.classList.add('ongoing');
			el.innerHTML = 'Query...';
			el.classList.remove('active');
			fetchOngoing = true;
			paramsChanged = false;
			const data = await fetchOnce() || await new Promise(resolve => {
				let delay = 300;
				const fetchfn = () => {
					fetchInterval = null;
					if (!fetchOngoing)
						return resolve(null);
					fetchOnce().then(ok => {
						if (fetchOngoing && (typeof ok === 'undefined' || (insistent && !ok))) {
							delay = delay<2000 ? (delay+50) : delay;
							if (insistent && !ok) delay = insistent;
							fetchInterval = setTimeout(fetchfn, delay);
						} else {
							resolve(ok);
						}
					});
				};
				fetchInterval = setTimeout(fetchfn, delay);
			});
			if (data && callbacks.data) callbacks.data(data);
		} else {
			el.innerHTML = 'Cancelled';
			if (progEl) progEl.innerHTML = '';
		}
		fetchOngoing = false;
		el.classList.remove('ongoing');
		if (paramsChanged) {
			setTimeout(() => {
				el.classList.add('active');
				el.innerHTML = 'Query data';
			}, 500);
		}
	};
	el.addEventListener('click', () => initFetch());
	if (progEl) div.append(progEl);
	div.append(el);
	return {
		params: (p, force) => {
			params = p;
			if (!fetchParams || !Object.keys(p).every(k => fetchParams[k] === p[k])) {
				if (force)
					return initFetch(p);
				if (!fetchOngoing) {
					el.classList.add('active');
					el.innerHTML = 'Query data';
				} else {
					paramsChanged = true;
				}
			} else {
				el.classList.remove('active');
				el.innerHTML = 're-query';
			}
		},
		fetch: initFetch,
		stop: () => {
			clearInterval(fetchInterval);
			fetchInterval = null;
		},
		el: div
	};
}

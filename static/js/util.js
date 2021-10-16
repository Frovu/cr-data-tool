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

export function encodeParams(obj) {
	const keys = Object.keys(obj);
	return keys.length ? '?' + keys.map(k => `${k}=${obj[k]}`).join('&') : '';
}

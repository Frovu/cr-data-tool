
export function fill(tab, items) {
	const el = document.getElementById(`${tab}-tab`);
	el.append(...items);
}

export function input(type, callback, options) {
	let elem;
	if (type === 'time') {
		elem = document.createElement('div');


	} else if (type === 'query') {
		elem = document.createElement('button');
		elem.classList.add('submit');
		elem.innerHTML = 'Submit';
		if (callback) elem.addEventListener('click', callback);
	} else if (type === 'switch') {
		elem = document.createElement('button');
		elem.classList.add('switch-input');
		elem.innerHTML = options.text + options.options[0];
		let current = 0;
		elem.addEventListener('click', () => {
			current = ++current >= options.options.length ? 0 : current;
			const opt = options.options[current];
			elem.innerHTML = options.text + opt;
			callback(opt);
		});
	}
	return elem;
}

export function disable(tab) {
	const button = document.getElementById(`${tab}-btn`);
	button.disabled = true;
}

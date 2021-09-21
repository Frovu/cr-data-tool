
export function fill(tab, items) {
	const el = document.getElementById(`${tab}-tab`);
	el.append(...items);
}

export function input(type, callback, options) {
	let elem;
	if (type === 'time') {
		elem = document.createElement('div');
		elem.classList.add('time-input');
		const from = document.createElement('input');
		const to = document.createElement('input');
		from.value = options.from.toISOString().replace(/T.*/, '') || '';
		to.value = options.to.toISOString().replace(/T.*/, '') || '';
		const submitChange = force => {
			const dateFrom = new Date(from.value);
			const dateTo = new Date(to.value);
			if (!isNaN(dateFrom) && !isNaN(dateTo))
				callback(dateFrom, dateTo, force);
		};
		[ from, to ].forEach(box => {
			box.onkeypress = e => { if (e.keyCode === 13) submitChange(true); };
			box.onchange = () => {
				if (isNaN(new Date(box.value)))
					return box.classList.add('invalid');
				box.classList.remove('invalid');
				submitChange();
			};
		});
		elem.append('from', from, 'to', to);
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

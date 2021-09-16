
export function fill(tab, items) {
	const el = document.getElementById(`${tab}-tab`);
	el.append(...items);
}

export function input(type, callback) {
	let elem;
	if (type === 'query') {
		elem = document.createElement('button');
		elem.classList.add('submit');
		elem.innerHTML = 'Submit';
		if (callback) elem.addEventListener('click', callback);
	}
	return elem;
}

export function disable(tab) {
	const button = document.getElementById(`${tab}-btn`);
	button.disabled = true;
}

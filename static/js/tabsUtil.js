import * as exportM from './export.js';
export const exportTab = exportM.exportTab;

export function fill(tab, items) {
	const el = document.getElementById(`${tab}-tab`);
	el.append(...items);
	const button = document.getElementById(`${tab}-btn`);
	button.disabled = false;
}

export function text(html) {
	const el = document.createElement('div');
	el.innerHTML = html;
	return el;
}

export function input(type, callback, options = {}) {
	let elem;
	if (type === 'station') {
		elem = document.createElement('div');
		elem.classList.add('station-input');
		if (options.text) elem.append(options.text);
		const sel = document.createElement('select');
		const lat = document.createElement('input');
		const lon = document.createElement('input');
		lat.type = lon.type = 'textbox';
		lat.value = options.lat || '';
		lon.value = options.lon || '';
		lat.disabled = lon.disabled = true;
		options.list.forEach(s => {
			const ss = options.lat === s.lat && options.lon === s.lon;
			sel.innerHTML += `<option value="${s.name}" ${ss?'selected':''}>${s.name}</option>`;
		});
		sel.onchange = () => {
			const st = options.list.find(s => s.name === sel.value);
			lat.value = st.lat;
			lon.value = st.lon;
			callback(st.lat, st.lon, st.name, st.desc);
		};
		elem.append(sel, 'lat=', lat, 'lon=', lon);
	} else if (type === 'station-only') {
		elem = document.createElement('div');
		elem.classList.add('station-input');
		if (options.text) elem.append(options.text);
		const sel = document.createElement('select');
		sel.innerHTML = options.list.map(s =>
			`<option value="${s.name}" ${s.name===options.selected?'selected':''}>${s.name}</option>`).join('\n');
		sel.onchange = () => callback(sel.value);
		elem.append(sel);
	} else if (type === 'station-channel') {
		elem = document.createElement('div');
		elem.classList.add('station-input');
		if (options.text) elem.append(options.text);
		const sel = document.createElement('select');
		const channelSel = document.createElement('select');
		sel.innerHTML = options.list.map(s =>
			`<option value="${s.name}" ${s.name===options.station?'selected':''}>${s.name}</option>`).join('\n');
		const updateChannels = sn => {
			const st = options.list.find(s => s.name === sn);
			channelSel.innerHTML = st && st.channels.map(c =>
				`<option value="${c}" ${c===options.channel?'selected':''}>${c}</option>`).join('\n');
		};
		updateChannels(options.station || options.list[0].name);
		sel.onchange = () => {
			updateChannels(sel.value);
			callback(sel.value, channelSel.value);
		};
		channelSel.onchange = () => callback(sel.value, channelSel.value);
		elem.append(sel, channelSel);
	} else if (type === 'timestamp') {
		elem = document.createElement('div');
		elem.classList.add('text-input');
		const inp = document.createElement('input');
		inp.value = new Date(options.value*1000).toISOString().replace(/T.*/, '') || '';
		const submitChange = force => {
			const date = new Date(inp.value);
			if (!isNaN(date))
				callback(Math.floor(date.getTime() / 1000), force);
		};
		inp.onkeypress = e => { if (e.keyCode === 13) submitChange(true); };
		inp.onchange = () => {
			if (isNaN(new Date(inp.value)))
				return inp.classList.add('invalid');
			inp.classList.remove('invalid');
			submitChange();
		};
		const footer = document.createElement('p');
		footer.classList.add('footer');
		footer.innerHTML = 'date format: yyyy-mm-dd';
		elem.append('at date', inp, footer);
	} else if (type === 'time') {
		elem = document.createElement('div');
		elem.classList.add('text-input');
		const from = document.createElement('input');
		const to = document.createElement('input');
		from.value = new Date(options.from*1000).toISOString().replace(/T.*/, '') || '';
		to.value = new Date(options.to*1000).toISOString().replace(/T.*/, '') || '';
		const submitChange = force => {
			const dateFrom = new Date(from.value);
			const dateTo = new Date(to.value);
			if (!isNaN(dateFrom) && !isNaN(dateTo))
				callback(Math.floor(dateFrom.getTime() / 1000),
					Math.floor(dateTo.getTime() / 1000), force);
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
		const footer = document.createElement('p');
		footer.classList.add('footer');
		footer.innerHTML = 'date format: yyyy-mm-dd';
		elem.append('from', from, 'to', to, footer);
	} else if (type === 'switch') {
		elem = document.createElement('button');
		elem.innerHTML = options.active || options.options[0];
		let current = options.active ? options.options.indexOf(options.active) : 0;
		elem.addEventListener('click', () => {
			current = ++current >= options.options.length ? 0 : current;
			const opt = options.options[current];
			elem.innerHTML = opt;
			callback(opt);
		});
		const span = document.createElement('label');
		span.classList.add('switch-input');
		span.innerHTML = options.text || '';
		span.append(elem);
		return span;
	} else if (type === 'checkbox') {
		elem = document.createElement('label');
		const box = document.createElement('input');
		box.type = 'checkbox';
		elem.onclick = () => { callback(box.checked); };
		elem.append(box, ' ', options.text);
	} else if (type === 'text') {
		const div = document.createElement('div');
		div.classList.add('text-input');
		elem = document.createElement('input');
		if (options.width)
			elem.style.width = options.width+'px';
		elem.value = options.value || '';
		elem.placeholder = options.placeholder || '';
		elem.onchange = () => callback(elem.value);
		if (options.label) {
			const lbl = document.createElement('span');
			lbl.innerHTML = options.label;
			div.append(lbl, elem);
			return div;
		} else {
			div.append( elem);
		}
		return div;
	} else if (type === 'query') {
		const optParams = options.params || {};
		const getParams = typeof optParams === 'function' ? optParams : () => optParams;
		let target = options.url;
		const text = options.text || 'Query';
		elem = document.createElement('button');
		elem.classList.add('submit');
		elem.classList.add('subquery');
		elem.innerHTML = text;
		elem.onclick = async () => {
			elem.innerHTML = '...';
			const method = options.method || 'GET';
			const params = getParams();
			const keys = Object.keys(params);
			const param = keys.length ? keys.map(k => `${k}=${encodeURIComponent(params[k])}`).join('&') : '';
			const res = await fetch(target + (method === 'GET' ? '?'+param : ''), {
				headers: {'Content-Type': 'application/x-www-form-urlencoded'},
				body: options.method === 'POST' ? param : null,
				method
			});
			elem.innerHTML = res.status;
			if (res.status === 200) {
				callback(await res.json());
			} else {
				elem.classList.add('error');
				console.log(target, res.status, await res.json().catch(()=>{}));
			}
			setTimeout(() => {
				elem.classList.remove('error');
				elem.innerHTML = text;
			}, 2000);
		};
		return {
			elem,
			fetch: elem.onclick
		};
	}
	return elem;
}

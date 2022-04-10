function textTable(data, fields) {
	if (!data) return 'no data';
	const len = data[0].length;
	const colLen = data[0].map((v, i) => fields[i].length < (String(v).length + 4) ? String(v).length + 4 : fields[i].length + 1);
	const paddings = colLen.map(l => ' '.repeat(l));
	const lineLen = colLen.reduce((a, b) => a + b, 0);
	let text = fields.map((f, i) => (f + paddings[i]).slice(0, colLen[i])).join('') + '\r\n';
	text += '-'.repeat(lineLen) + '\r\n';
	data.forEach(line => {
		for (let i = 0; i < len; ++i) {
			const val = line[i].toString() + paddings[i];
			text += val.slice(0, colLen[i]);
		}
		text += '\r\n';
	});
	return text;
}

function exportToFile(data, fields, filename, download=false) {
	const dataUrl = 'data:,' + encodeURIComponent(textTable(data, fields));
	if (download) {
		const a = document.createElement('a');
		a.href = dataUrl;
		a.download = filename + '.txt';
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
	} else {
		window.open(dataUrl, '_blank');
	}
}

export function exportTab(urlBase, params, filename='crdt-data') {
	let data, fields, fname = filename;
	const el = document.createElement('div');
	const textEl = document.createElement('button');
	textEl.onclick = () => exportToFile(data, fields, fname, true);
	textEl.innerHTML = 'download .txt';
	const urlEl = document.createElement('p');
	el.append(textEl, urlEl);
	return {
		setData: (d, f) => {
			data = d;
			fields = f;
		},
		setParams: p => {
			params = p;
			const url = urlBase +'?'+ Object.keys(p).map(k => `${k}=${p[k]}`).join('&');
			urlEl.innerHTML = `Every dataset is also available <a href="${url}">via API<a>`;
		},
		el
	};
}

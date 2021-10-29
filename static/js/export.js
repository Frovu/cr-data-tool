function exportToFile(data, fields, filename, download=false) {
	let text = fields.join('\t');
	for (const r of data)
		text += '\n' + r.join('\t');
	const dataUrl = 'data:,' + encodeURIComponent(text);
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

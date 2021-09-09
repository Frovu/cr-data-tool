async function query() {
	return await fetch('api/temp/?from=1630067000&to=1641199298&lat=55.47&lon=37.32', { method: 'GET' });
}

async function fetchData() {
	const progress = document.getElementById('progress');
	for (let loop = true; loop;) {
		const resp = await query().catch(()=>{});
		if (resp && resp.status === 200) {
			const body = await resp.json().catch(()=>{});
			console.log(body)
			if (body.status === 'ok') {
				console.log('done');
				break;
			} else if (body.status === 'busy') {
				progress.innerHTML = body.download ? `Downloading: ${body.download}` : 'Calculating';
			} else if (body.status === 'unknown') {
				// TODO:
			}
		} else {
			console.log('request failed', resp && resp.status);
		}
	}

}

const btn = document.getElementById('button');
btn.onclick = fetchData;

export function ping() {
	// console.log('temperature');
}

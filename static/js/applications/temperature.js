async function query() {
	return await fetch('api/temp/?from=1580504400&to=1641199298&lat=55.47&lon=37.32', { method: 'GET' });
}

async function fetchData() {
	const progress = document.getElementById('progress');
	const resp = await query().catch(()=>{});
	if (resp && resp.status === 200) {
		const body = await resp.json().catch(()=>{});
		if (body.status === 'ok') {
			progress.innerHTML = 'done!';
			return true;
		} else if (body.status === 'busy') {
			progress.innerHTML = body.download ? `Downloading: ${(100*body.download).toFixed(0)} %` : 'Calculating';
		} else if (body.status === 'unknown') {
			// TODO:
		}
	} else {
		console.log('request failed', resp && resp.status);
	}
}

function startFetch() {
	fetchData().then(ok => {
		if (!ok) {
			const interval = setInterval(() => {
				fetchData().then(okk => {
					if (okk) clearInterval(interval);
				});
			}, 1000);
		}
	});
}

const btn = document.getElementById('button');
btn.onclick = startFetch;

export function ping() {
	// console.log('temperature');
}

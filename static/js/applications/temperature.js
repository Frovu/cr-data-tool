async function query() {
	return await fetch('api/temp/?from=1580504400&to=1641199298&lat=55.47&lon=37.32', { method: 'GET' });
}

async function fetchTry() {
	const progress = document.getElementById('progress');
	const resp = await query().catch(()=>{});
	if (resp && resp.status === 200) {
		const body = await resp.json().catch(()=>{});
		if (body.status === 'ok') {
			progress.innerHTML = 'done!';
			return body;
		} else if (body.status === 'busy') {
			progress.innerHTML = body.download ? `Downloading: ${(100*body.download).toFixed(0)} %` : 'Calculating';
		} else if (body.status === 'unknown') {
			// TODO:
		}
	} else {
		console.log('request failed', resp && resp.status);
	}
}

export function fetchData() {
	return new Promise(resolve => {
		fetchTry().then(ok => {
			if (!ok) {
				const interval = setInterval(() => {
					fetchTry().then(okk => {
						if (okk) {
							resolve(okk);
							clearInterval(interval);
						}
					});
				}, 1000);
			} else {
				resolve(ok);
			}
		});
	});
}

export function ping() {
	// console.log('temperature');
}

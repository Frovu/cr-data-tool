import uPlot from 'uplot';

export function customTimeSplits(): Partial<uPlot.Axis> {
	return {
		splits: (u, ax, min, max, incr, space) => {
			const num = Math.floor(u.width / 76);
			const width = Math.ceil((max - min) / num);
			const split = ([ 24, 48, 72, 120, 240, 720 ].find(s => width <= s * 3600) || 48) * 3600;
			const start = Math.ceil(min / split) * split;
			const limit = Math.ceil((max - split/4 - start) / split);
			return Array(limit).fill(1).map((a, i) => start + i * split);
		},
		values: (u, splits) => splits.map((v, i) => {
			if (v % 86400 !== 0)
				return null;
			const d = new Date(v * 1e3);
			const month = String(d.getUTCMonth() + 1).padStart(2, '0');
			const day = String(d.getUTCDate()).padStart(2, '0');
			const showYear = (v - splits[0] < 86400) && String(d.getUTCFullYear());
			return (showYear ? showYear + '-' : '     ') + month + '-' + day;
		}),
		gap: 6,
		size: 32,
	};
}

export function color(name: string, opacity=1) {
	const col = window.getComputedStyle(document.body).getPropertyValue('--color-'+name) || 'red';
	const parts = col.includes('rgb') ? col.match(/[\d.]+/g)!.slice(0,3) :
		(col.startsWith('#') ? [1,2,3].map(d => parseInt(col.length===7 ? col.slice(1+(d-1)*2, 1+d*2) : col.slice(d, 1+d), 16) * (col.length===7 ? 1 : 17 )) : null);
	return parts ? `rgba(${parts.join(',')},${opacity})` : col;
}

export function font(size=16, scale=false) {
	const fnt = window.getComputedStyle(document.body).font;
	return fnt.replace(/\d+px/, (scale ? Math.round(size * devicePixelRatio) : size) + 'px');
}

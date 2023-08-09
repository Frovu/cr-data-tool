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

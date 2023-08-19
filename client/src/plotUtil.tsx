import { SetStateAction, createContext, useContext, useMemo, useState } from 'react';
import uPlot from 'uplot';
import { useSize } from './util';
import UplotReact from 'uplot-react';

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

export type NavigationState = {
	cursor: { idx: number, lock: boolean } | null,
	selection: { min: number, max: number } | null,
	view: { min: number, max: number }
};
export const NavigationContext = createContext<{ state: NavigationState, setState: (a: SetStateAction<NavigationState>) => void }>({} as any);
export function useNavigationState() {
	const [state, setState] = useState<NavigationState>({
		cursor: null, selection: null, view: { min: 0, max: 0 }
	});
	return { state, setState };
}

export function NavigatedPlot({ data, options: opts }: { data: number[][], options: Omit<uPlot.Options, 'width'|'height'> }) {
	const { state: { cursor, selection, view }, setState } = useContext(NavigationContext);
	
	const [container, setContainer] = useState<HTMLDivElement | null>(null);
	const size = useSize(container?.parentElement);
	const [u, setUplot] = useState<uPlot>();
	

	const plot = useMemo(() => {
		const options: uPlot.Options = {
			...opts, ...size,
			tzDate: ts => uPlot.tzDate(new Date(ts * 1e3), 'UTC'),
		};
		return <UplotReact {...{ options, data: data as any, onCreate: setUplot }}/>;
	}, [data, opts]);

	return (<div ref={node => setContainer(node)} style={{ position: 'absolute' }}>
		{plot}
	</div>);
}
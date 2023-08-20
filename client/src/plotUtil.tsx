import { SetStateAction, createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
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
	focused: { idx: number, label: string } | null,
	chosen: { idx: number, label: string } | null,
	view: { min: number, max: number }
};
export const NavigationContext = createContext<{ state: NavigationState, setState: (a: SetStateAction<NavigationState>) => void }>({} as any);
export function useNavigationState() {
	const [state, setState] = useState<NavigationState>({
		cursor: null, selection: null, focused: null, chosen: null, view: { min: 0, max: 0 }
	});
	return { state, setState };
}

export function NavigatedPlot({ data, options: opts }: { data: number[][], options: () => Omit<uPlot.Options, 'width'|'height'> }) {
	const { state: { cursor, selection, focused, chosen, view },
		setState } = useContext(NavigationContext);
	const set = useCallback((changes: Partial<NavigationState>) => setState(st => ({ ...st, ...changes })), [setState]);
	
	const [container, setContainer] = useState<HTMLDivElement | null>(null);
	const size = useSize(container?.parentElement);
	const [u, setUplot] = useState<uPlot>();

	useEffect(() => {
		console.log('eff cursor', u?.cursor.idx)
		cursor?.lock && u?.setCursor(cursor ? {
			left: u.valToPos(u.data[0][cursor.idx], 'x'),
			top: !focused ? u.cursor.top ?? 0 :
				u.valToPos(u.data[focused.idx][cursor.idx]!, u.series[focused.idx].scale!)
		} : { left: -1, top: -1 }, false);
		if (u && cursor)
			(u as any).cursor._lock = cursor.lock;
	}, [u, cursor, focused]);

	useEffect(() => {
		console.log('eff selection')
		const left = selection && u?.valToPos(u.data[0][selection.min], 'x');
		u?.setSelect(u && selection ? {
			width: u.valToPos(u.data[0][selection.max], 'x') - left!,
			height: u.over.offsetHeight, top: 0, left: left!
		}: { left: 0, top: 0, width: 0, height: 0 }, false);
	}, [u, selection]);

	useEffect(() => {
		if (!u) return;
		(u as any)._chosen = chosen?.label;
		u.redraw(false, true);
	}, [u, chosen]);

	useEffect(() => {
		console.log('eff size')
		u?.setSize(size);
		set({ cursor: null, selection: null });
	}, [u, size, set]);

	useEffect(() => {
		console.log('eff data')
		// const xScale = { min: data[0][0], max: data[0][data[0].length-1] };
		// console.log(!!u, !!data, u?.data)
		u?.setData(data as any, true);
		// u?.redraw(true, true);
		// u?.setScale('x', xScale)
		// console.log(u?.scales.x)
	}, [u, data]);

	const plot = useMemo(() => {
		if (!data) return null;
		const uOpts = opts();
		let selectingWithMouse = false;
		const options: uPlot.Options = {
			...uOpts, ...size,
			tzDate: ts => uPlot.tzDate(new Date(ts * 1e3), 'UTC'),
			cursor: {
				points: {
					size: 6,
					fill: color('acid'),
					stroke: color('acid')
				},
				focus: { prox: 32 },
				drag: { dist: 10 },
				bind: {
					dblclick: (upl: any) => () => {
						upl.cursor._lock = true;
						return null;
					},
					mousedown: (upl, targ, handler) => e => {
						handler(e);
						if (e.button !== 0) return null;
						upl.setSelect({ left: 0, top: 0, width: 0, height: 0 }, false);
						if (!e.ctrlKey && !e.shiftKey)
							selectingWithMouse = true;
						return null;
					},
					mouseup: (upl: any, targ, handler) => e => {
						if (e.button !== 0) return null;
						if (selectingWithMouse) {
							upl.cursor.drag.setScale = false;
							handler(e);
							upl.cursor.drag.setScale = true;
							if (upl.select?.width <= 0) {
								set({ cursor: upl.cursor.idx == null ? null :
									{ idx: upl.cursor.idx, lock: (upl as any).cursor._lock } });
							} else {
								upl.cursor._lock = false;
							}
						} else {
							handler(e);
							upl.setSelect({ left: 0, top: 0, width: 0, height: 0 }, true);
						}
						selectingWithMouse = false;
						return null;
					}
				},
				lock: true
			},
			focus: {
				alpha: 1.1
			},
			hooks: {
				setCursor: [
					(upl: any) => setState(st => (upl.cursor.idx !== st.cursor?.idx || upl.cursor._lock !== st.cursor?.lock)
						? ({ ...st, cursor: upl.cursor.idx == null ? null
							: { idx: upl.cursor.idx, lock: upl.cursor._lock } }) : st)
				],
				setScale: [
					(upl: uPlot) => set({ view: {
						min: upl.valToIdx(upl.scales.x.min!),
						max: upl.valToIdx(upl.scales.x.max!) } })
				],
				setSelect: [
					(upl: uPlot) => set({ selection:
						upl.select && upl.select.width ? {
							min: upl.posToIdx(upl.select.left),
							max: upl.posToIdx(upl.select.left + upl.select.width)
						} : null })
				],
				setSeries: [
					(upl: any, si: any) => upl.series[si]?._focus
						&& set({ focused: { idx: si, label: upl.series[si].label } })
				]
			}
		};
		return <UplotReact {...{ options, data: data as any, onCreate: setUplot }}/>;
	}, [!!data, opts, setState]);

	return (<div ref={node => setContainer(node)} style={{ position: 'absolute' }}>
		{size.width > 0 && plot}
	</div>);
}
import React, { ReactElement, Reducer, SetStateAction, useCallback, useEffect, useLayoutEffect, useReducer, useRef, useState } from 'react';

export function prettyDate(inp: Date | number | null, short=false) {
	if (inp == null) return 'N/A';
	const date = inp instanceof Date ? inp : new Date(1e3 * inp);
	return isNaN(date.getTime()) ? 'Invalid' : date.toISOString().replace('T', ' ').replace(short ? /\s.*/ : /(:00)?\..*/, '');
}

export const clamp = (min: number, max: number, val: number, minFirst: boolean=false) =>
	minFirst ? Math.min(max, Math.max(min, val)) : Math.max(min, Math.min(max, val));

export async function apiPost<T = { message?: string }>(url: string, body?: { [k: string]: any }): Promise<T> {
	const res = await fetch(process.env.REACT_APP_API + 'api/' + url, {
		method: 'POST', credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: body && JSON.stringify(body)
	});
	const json = await res.json().catch(() => {});
	if (!json || res.status !== 200)
		throw new Error(json?.message ?? ('HTTP '+res.status));
	return json;
}
export async function apiGet<T = { message?: string }>(url: string, query?: { [k: string]: any }): Promise<T> {
	let uri = process.env.REACT_APP_API + 'api/' + url;
	if (query)
		uri += '?' + new URLSearchParams(query).toString();
	const res = await fetch(uri, { credentials: 'include' });
	const json = await res.json().catch(() => {});
	if (!json || res.status !== 200)
		throw new Error(json?.message ?? ('HTTP '+res.status));
	return json;
}

export function dispatchCustomEvent(eventName: string, detail?: {}) {
	document.dispatchEvent(new CustomEvent(eventName, { detail }));
}

export function useEventListener(eventName: string, callback: (e: any) => void | (() => void), elementRef?: React.RefObject<HTMLElement>) {
	const savedCallback = useRef(callback);
	savedCallback.current = callback;

	useEffect(() => {
		const listener: typeof callback = (e) => savedCallback.current(e);
		const target = elementRef?.current ?? document; 
		target.addEventListener(eventName, listener as any);
		return () => target.removeEventListener(eventName, listener as any);
	}, [elementRef, eventName]);
}

export function usePersistedState<T>(key: string, initial: (() => T) | T): [T, (a: SetStateAction<T>) => void]  {
	const [state, setState] = useState<T>(() => {
		const stored = window.localStorage.getItem(key);
		const def = typeof initial === 'function' ? (initial as any)() : initial;
		try {
			return { ...def, ...(stored && JSON.parse(stored)) };
		} catch {
			console.warn('Failed to parse state: ' + key);
			return def;
		}
	});

	const setter = useCallback((arg: SetStateAction<T>) => setState(prev => {
		const value = typeof arg === 'function' ? (arg as any)(prev) : arg;
		window.localStorage.setItem(key, JSON.stringify(value));
		return value;
	}), [key]);
	
	return [state, setter];
}
 
type ResizeInfo = { width: number, height: number };
export function useResizeObserver<T extends HTMLElement>(target: T | null | undefined, callback: (e: ResizeInfo) => void) {
	const savedCallback = useRef(callback);
	savedCallback.current = callback;
	
	useLayoutEffect(() => {
		if (!target) return;
		const observer = new ResizeObserver(() => {
			savedCallback.current({ width: target.offsetWidth - 2, height: target.offsetHeight - 2 });
		});
		observer.observe(target);
		return () => observer.unobserve(target);
	}, [target]);
}

export function useSize<T extends HTMLElement>(target: T | null | undefined) {
	const [ size, setSize ] = useState({ width: 0, height: 0 });

	useResizeObserver(target, newSize => {
		setSize(oldSize => {
			if (oldSize.width !== newSize.width || oldSize.height !== newSize.height)
				return newSize;
			return oldSize;
		});
	});

	return size;
}

const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export function useMonthInput(initial?: Date, initialMonths?: number, maxMonths?: number) {
	type R = Reducer<{ year: number, month: number, count: number, interval: number[]}, { action: 'month'|'year'|'count', value: number }>;
	const init = initial ?? new Date();
	const [{ year, month, count, interval }, dispatch] = useReducer<R>((state, { action, value }) => {
		const st = { ...state, [action]: value };
		st.interval = [0, st.count].map(inc => new Date(Date.UTC(st.year, st.month + inc)).getTime() / 1e3);
		return st;
	}, {
		year: init.getFullYear(),
		month: init.getMonth(),
		count: initialMonths ?? 1,
		interval: [0, initialMonths ?? 1].map(inc => new Date(Date.UTC(init.getFullYear(), init.getMonth() + inc)).getTime() / 1e3)
	});
	const set = (action: 'month'|'year'|'count', value: number) => dispatch({ action, value });

	return [interval, <div style={{ display: 'inline-block' }}>
		<select onWheel={e => set('month', Math.max(0, Math.min(month + Math.sign(e.deltaY), 11)))}
			value={monthNames[month]} onChange={e => set('month', monthNames.indexOf(e.target.value))}>
			{monthNames.map(mon => <option key={mon} id={mon}>{mon}</option>)}
		</select> <input style={{ width: '6ch' }} type='number' min='1957' max={new Date().getFullYear()}
			value={year} onChange={e => !isNaN(e.target.valueAsNumber) && set('year', e.target.valueAsNumber)}
		/> + <input style={{ width: '4ch', textAlign: 'center' }} type='number' min='1' max={maxMonths ?? 24}
			value={count} onChange={e => !isNaN(e.target.valueAsNumber) && set('count', e.target.valueAsNumber)}
		/> month{count === 1 ? '' : 's'}
	</div>] as [number[], ReactElement];
}
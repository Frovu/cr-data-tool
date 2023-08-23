import React, { SetStateAction, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

export function prettyDate(date: Date) {
	return isNaN(date.getTime()) ? 'Invalid' : date.toISOString().replace('T', ' ').replace(/(:00)?\..*/, '');
}

export async function apiPost(url: string, body: { [k: string]: any }, resolve=true) {
	const res = await fetch(process.env.REACT_APP_API + 'api/' + url, {
		method: 'POST', credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (!resolve)
		return res;
	if (res.status !== 200)
		throw new Error('HTTP '+res.status);
	return await res.json();
}
export async function apiGet(url: string, query?: { [k: string]: any }) {
	let uri = process.env.REACT_APP_API + 'api/' + url;
	if (query)
		uri += '?' + new URLSearchParams(query).toString();
	const res = await fetch(uri, { credentials: 'include' });
	if (res.status !== 200)
		throw new Error('HTTP '+res.status);
	return await res.json();
}

export function dispatchCustomEvent(eventName: string, detail?: {}) {
	document.dispatchEvent(new CustomEvent(eventName, { detail }));
}

export function useEventListener(eventName: string, callback: (e: any) => any | (() => any), elementRef?: React.RefObject<HTMLElement>) {
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
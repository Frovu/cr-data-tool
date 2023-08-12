import { useQuery } from 'react-query';
import uPlot from 'uplot';
import { color, font } from '../plotUtil';
import UplotReact from 'uplot-react';
import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { useEventListener, useSize } from '../util';
import { createPortal } from 'react-dom';
import MinuteView from './MinuteView';

function plotOptions(stations: string[], levels: number[]) {
	const serColor = (u: any, idx: number) => {
		return u.series[idx].label === u._prime ? (u.series[idx]._focus ? color('gold') : color('green')) : u.series[idx]._focus ? color('orange') : color('cyan');
	};
	let mouseSelection = false;
	return {
		tzDate: ts => uPlot.tzDate(new Date(ts * 1e3), 'UTC'),
		legend: { show: false },
		padding: [10, 12, 6, 0],
		cursor: {
			points: {
				size: 6,
				fill: color('acid'),
				stroke: color('acid')
			},
			focus: { prox: 32 },
			bind: {
				dblclick: u => null,
				mousedown: (u, targ, handler) => {
					return e => {
						u.setSelect({ left: 0, top: 0, width: 0, height: 0 }, false);
						if (e.button === 0) {
							handler(e);
							if (!e.ctrlKey && !e.shiftKey) {
								mouseSelection = true;
							}
						}
						return null;
					};
				},
				mouseup: (u: any, targ, handler) => {
					return e => {
						if (e.button === 0) {
							if (mouseSelection) {
								u.cursor.drag.setScale = false;
								handler(e);
								u.cursor.drag.setScale = true;
								if (u.select?.width > 0)
									u.cursor._lock = false;
							} else {
								handler(e);
							}
							mouseSelection = false;
							return null;
						}
					};
				}
			},
			lock: true
		},
		focus: {
			alpha: 1.1
		},
		scales: {
			y: {
				range: (u, min, max) =>  [min - 2, max + 2]
			}
		},
		axes: [
			{
				font: font(14),
				stroke: color('text'),
				grid: { show: true, stroke: color('grid'), width: 2 },
				ticks: { stroke: color('grid'), width: 2 },
			},
			{
				splits: u => levels.map((lvl, i) => (((u.data[1 + i][0] ?? 0) + 2*lvl) / 3 + 2)),
				values: u => stations.map(s => s === (u as any)._prime ? s.toUpperCase() : s).map(s => s.slice(0, 4)),
				size: 36,
				gap: -6,
				font: font(12),
				stroke: color('text'),
				grid: { show: true, stroke: color('grid'), width: 2 },
			}
		],
		series: [
			{ value: '{YYYY}-{MM}-{DD} {HH}:{mm}', stroke: color('text') } as any
		].concat(stations.map(s => ({
			label: s,
			stroke: serColor,
			grid: { stroke: color('grid'), width: 1 },
			points: { fill: color('bg'), stroke: serColor },

		} as Partial<uPlot.Series>)))
	} as Omit<uPlot.Options, 'height'|'width'>;
}

function queryFunction(path: string, interval: [Date, Date], qStations: string[]) {
	return async () => {
		const urlPara = new URLSearchParams({
			from: (interval[0].getTime() / 1000).toFixed(0),
			to:   (interval[1].getTime() / 1000).toFixed(0),
			stations: qStations.join(),
		}).toString();
		const res = await fetch(process.env.REACT_APP_API + path + '?' + urlPara);
		if (res.status !== 200)
			throw Error('HTTP '+res.status);
		const body = await res.json() as { rows: any[][], fields: string[] };
		if (!body?.rows.length) return null;
		console.log(path, '=>', body);

		const stations = body.fields.slice(1);
		const time = body.rows.map(row => row[0]);
		const data = Array.from(stations.keys()).map(i => body.rows.map(row => row[i+1]));
		const averages = data.map((sd) => {
			const s = sd.slice().sort(), mid = Math.floor(sd.length / 2);
			return s.length % 2 === 0 ? s[mid] : (s[mid] + s[mid + 1]) / 2;
		});
		const sortedIdx = Array.from(stations.keys()).filter(i => averages[i] > 0).sort((a, b) => averages[a] - averages[b]);
		const distance = (averages[sortedIdx[sortedIdx.length-1]] - averages[sortedIdx[0]]) / sortedIdx.length;
		const spreaded = sortedIdx.map((idx, i) => data[idx].map(val => 
			val == null ? null : (val - averages[idx] - i * distance) ));

		return {
			data: [time, ...sortedIdx.map(i => data[i])],
			plotData: [time, ...spreaded],
			stations: sortedIdx.map(i => stations[i]),
			levels: sortedIdx.map((idx, i) => - i * distance)
		};
	};
}

export function ManyStationsView({ interval, legendContainer, detailsContainer }:
{ interval: [Date, Date], legendContainer: Element | null, detailsContainer: Element | null }) {
	const queryStations = ['all'];
	const query = useQuery(['manyStations', queryStations, interval], queryFunction('api/neutron', interval, queryStations));

	const [container, setContainer] = useState<HTMLDivElement | null>(null);
	const size = useSize(container?.parentElement);

	const [primaryStation, setPrimaryStation] = useState<string | null>(null);

	const [u, setUplot] = useState<uPlot>();
	// const [cursorIdx, setCursorIdx] = useState<number | null>(null);

	const [selection, setSelect] = useState<null | { min: number, max: number }>(null);
	const setSelection = (sel: null | { min: number, max: number }) => {
		if (!u) return;
		if (sel) {
			const left = u.valToPos(u.data[0][sel.min], 'x');
			u.setSelect({
				width: u.valToPos(u.data[0][sel.max], 'x') - left,
				height: u.over.offsetHeight, top: 0, left
			}, false);
		} else {
			u.setSelect({ left: 0, top: 0, width: 0, height: 0 }, false);
		}
		setSelect(sel);
	};

	useLayoutEffect(() => {
		u?.setSize(size);
		u?.setCursor({ left: -1, top: -1 });
		u?.setSelect({ left: 0, top: 0, width: 0, height: 0 });
	}, [u, size]);

	useEffect(() => {
		if (!u) return;
		(u as any)._prime = primaryStation;
		u.redraw(false, true);
	}, [u, primaryStation]);

	useEventListener('click', () => {
		u && u.cursor.idx && u.setCursor({ left: u.cursor.left!, top: u.cursor.top! });
	});
	useEventListener('dblclick', (e: MouseEvent) => {
		if (!u || !query.data) return;
		const ser = u.series.find((s: any) => s._focus && s.scale !== 'x');
		if (ser) setPrimaryStation(ser.label!);
	});
	useEventListener('keydown', (e: KeyboardEvent) => {
		if (!u || !query.data) return;
		const moveCur = { ArrowLeft: -1, ArrowRight: 1 }[e.key];
		const movePrime = { ArrowUp: -1, ArrowDown: 1 }[e.key];
		if (moveCur) {
			const data = query.data.plotData;
			const length = data[0].length;
			const left = u.valToIdx(u.scales.x.min!), right = u.valToIdx(u.scales.x.max!);
			const cur = u.cursor.idx ?? (moveCur < 0 ? right + 1 : left - 1);
			const move = moveCur * (e.ctrlKey ? Math.ceil(length / 64) : 1)
				* (e.altKey ? Math.ceil(length / 16) : 1);
			const idx = Math.max(left, Math.min(cur + move, right));
			const primeIdx = primaryStation == null ? null : query.data.stations.indexOf(primaryStation);
			const primePos = primeIdx == null ? null : u.valToPos(data[primeIdx + 1][idx] ?? query.data.levels[primeIdx], 'y');
			u.setCursor({ left: u.valToPos(data[0][idx], 'x'), top: primePos ?? u.cursor.top ?? 0 });
			if (primeIdx != null) u.setSeries(1 + primeIdx, { focus: true });
			setSelection((() => {
				if (!e.shiftKey) return null;
				const sel = selection;
				const vals = (!sel || !((cur !== sel.min) !== (cur !== sel.max)))
					? [cur, cur + move]
					: [cur + move, cur !== sel.min ? sel.min : sel.max];
				return vals[0] === vals[1] ? null : {
					min: Math.min(...vals),
					max: Math.max(...vals)
				};
			})());
		} else if (movePrime && e.ctrlKey) {
			const sts = query.data.stations;
			setPrimaryStation(p => {
				const idx = p ? Math.max(0, Math.min(sts.indexOf(p) + movePrime, sts.length - 1)) : movePrime < 0 ? sts.length - 1 : 0;
				console.log(idx);
				if (u.cursor.idx != null)
					u.setCursor({ left: u.cursor.left!, top: u.valToPos(query.data?.plotData[idx + 1][u.cursor.idx] ?? query.data?.levels[idx], 'y') });
				u.setSeries(1 + idx, { focus: true });
				return sts[idx];
			});
		} else if (e.code === 'KeyZ' && selection) {
			u.setScale('x', { min: u.data[0][selection.min], max: u.data[0][selection.max] });
			u.setCursor({ left: -1, top: -1 });
			setSelection(null);
		} else if (e.key === 'Escape') {
			u.setScale('x', { min: u.data[0][0], max: u.data[0][u.data[0].length-1] });
			u.setCursor({ left: -1, top: -1 });
			setSelection(null);
		}
	});

	const [legend, setLegend] = useState<{ name: string, value: number, focus: boolean }[] | null>(null); 
	const plot = useMemo(() => {
		if (!query.data) return null;
		const { data, plotData, stations } = query.data;
		const options = { ...size, ...plotOptions(stations, query.data.levels), hooks: {
			setLegend: [
				(upl: uPlot) => {
					const idx = upl.legend.idx;
					if (idx == null)
						return setLegend(null);
					setLegend(stations.map((s, si) =>
						({ name: s.toUpperCase().slice(0, 4), value: data[1 + si][idx], focus: (upl.series[1 + si] as any)._focus })));
				}
			],
			// setCursor: [
			// 	(upl: any) => setCursorIdx(upl.cursor._lock ? upl.cursor.idx : null)
			// ],
			setSelect: [
				(upl: uPlot) => setSelect(upl.select ? {
					min: upl.posToIdx(upl.select.left),
					max: upl.posToIdx(upl.select.left + upl.select.width)
				} : null)
			],
			setSeries: [
				(upl: any, si: any) => upl.setLegend({ idx: upl.legend.idx })
			]
		} };
		return <UplotReact {...{ options, data: plotData as any, onCreate: setUplot }}/>;
	// Size changes are done through useEffect, without reiniting whole plot
	}, [query.data]); // eslint-disable-line

	if (query.isLoading)
		return <div className='center'>LOADING...</div>;
	if (query.isError)
		return <div className='center' style={{ color: color('red') }}>FAILED TO LOAD</div>;
	if (!query.data)
		return <div className='center'>NO DATA</div>;
	
	const focusedStation = legend?.find((s) => s.focus)?.name ?? primaryStation;
	return (<div ref={node => setContainer(node)} style={{ position: 'absolute' }}>
		{plot}
		{legendContainer && createPortal((
			<>
				<div style={{ margin: '0 0 4px 16px' }}>
					Primary station: <select style={{ color: primaryStation ? 'var(--color-green)' : 'var(--color-text)' }} 
						value={primaryStation ?? 'none'} onChange={e => setPrimaryStation(e.target.value === 'none' ? null : e.target.value)}>
						<option value='none'>none</option>
						{query.data.stations.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
					</select>
				</div>
				{legend && <div style={{ display: 'grid', border: '2px var(--color-border) solid', padding: '2px 4px',
					gridTemplateColumns: 'repeat(3, 120px)' }}>
					{legend.map(({ name, value, focus }) =>
						<span key={name} style={{ color: color(focus ? 'magenta' : value == null ? 'text-dark' : 'text') }}>{name}={value == null ? 'N/A' : value.toFixed(1)}</span>)}
				</div>}
			</>
		), legendContainer)}
		{focusedStation && u?.cursor.idx && detailsContainer && createPortal((
			<div style={{ position: 'relative', border: '2px var(--color-border) solid', width: 356, height: 240 }}>
				<MinuteView {...{ station: focusedStation, timestamp: u!.data[0][u?.cursor.idx] }}/>
			</div>
		), detailsContainer)}
	</div>);
}
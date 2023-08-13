import uPlot from 'uplot';
import { color, font } from '../plotUtil';
import UplotReact from 'uplot-react';
import { useContext, useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { useEventListener, useSize } from '../util';
import { createPortal } from 'react-dom';
import MinuteView from './MinuteView';
import { NeutronContext } from './Neutron';

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
			drag: { dist: 10 },
			bind: {
				dblclick: (u: any) => () => { u.cursor._lock = true; return null; },
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
				splits: u => levels.map((lvl, i) => (((u.data[1 + i + levels.length][0] ?? lvl) + 2*lvl) / 3 + 2)),
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
			width: 1,
			stroke: color('purple', .9),
			points: { show: true, size: 4, fill: color('purple', .5), stroke: color('purple', .4) },
		} as Partial<uPlot.Series>))).concat(stations.map(s => ({
			label: s,
			stroke: serColor,
			grid: { stroke: color('grid'), width: 1 },
			points: { fill: color('bg'), stroke: serColor },
		} as Partial<uPlot.Series>)))
	} as Omit<uPlot.Options, 'height'|'width'>;
}

export function ManyStationsView({ interval, legendContainer, detailsContainer }:
{ interval: [Date, Date], legendContainer: Element | null, detailsContainer: Element | null }) {
	const {
		data, plotData, primeStation, stations, levels, selectedRange, setCursorIdx, setPrimeStation, setSelectedRange, setViewRange
	} = useContext(NeutronContext)!;

	const [container, setContainer] = useState<HTMLDivElement | null>(null);
	const size = useSize(container?.parentElement);

	const [u, setUplot] = useState<uPlot>();
	const [legend, setLegend] = useState<{ name: string, value: number, focus: boolean }[] | null>(null); 
	const focusedStation = stations.find(st => st.toUpperCase().startsWith(legend?.find((s) => s.focus)?.name!)) ?? primeStation;

	useEffect(() => {
		if (!u) return;
		if (selectedRange) {
			const left = u.valToPos(u.data[0][selectedRange[0]], 'x');
			u.setSelect({
				width: u.valToPos(u.data[0][selectedRange[1]], 'x') - left,
				height: u.over.offsetHeight, top: 0, left
			}, false);
		} else {
			u.setSelect({ left: 0, top: 0, width: 0, height: 0 }, false);
		}
	}, [u, selectedRange]);

	useEffect(() => {
		u?.setData(plotData as any, false);
		u?.redraw();
	}, [u, plotData]);

	useLayoutEffect(() => {
		u?.setSize(size);
		u?.setCursor({ left: -1, top: -1 });
		u?.setSelect({ left: 0, top: 0, width: 0, height: 0 });
	}, [u, size]);

	useEffect(() => {
		if (!u) return;
		(u as any)._prime = primeStation;
		u.redraw(false, true);
	}, [u, primeStation]);

	useEventListener('click', () => {
		u && u.cursor.idx && u.setCursor({ left: u.cursor.left!, top: u.cursor.top! });
	});
	useEventListener('dblclick', (e: MouseEvent) => {
		if (!u) return;
		const ser = u.series.find((s: any) => s._focus && s.scale !== 'x');
		setCursorIdx((u as any).cursor._lock ? u.cursor.idx! : null);
		if (ser) setPrimeStation(ser.label!);
	});
	useEventListener('keydown', (e: KeyboardEvent) => {
		if (!u) return;
		const moveCur = { ArrowLeft: -1, ArrowRight: 1 }[e.key];
		const movePrime = { ArrowUp: -1, ArrowDown: 1 }[e.key];
		const sidx = (i: number) => i + stations.length + 1;
		if (moveCur) {
			const length = plotData[0].length;
			const left = u.valToIdx(u.scales.x.min!), right = u.valToIdx(u.scales.x.max!);
			const cur = u.cursor.idx ?? (moveCur < 0 ? right + 1 : left - 1);
			const move = moveCur * (e.ctrlKey ? Math.ceil(length / 64) : 1)
				* (e.altKey ? Math.ceil(length / 16) : 1);
			const idx = Math.max(left, Math.min(cur + move, right));
			const primeIdx = primeStation == null ? null : stations.indexOf(primeStation);
			const primePos = primeIdx == null ? null : u.valToPos(plotData[sidx(primeIdx)][idx] ?? levels[primeIdx], 'y');
			u.setCursor({ left: u.valToPos(plotData[0][idx], 'x'), top: primePos ?? u.cursor.top ?? 0 }, false);
			(u as any).cursor._lock = true;
			setCursorIdx(idx);
			if (primeIdx != null) u.setSeries(sidx(primeIdx), { focus: true });
			setSelectedRange((() => {
				if (!e.shiftKey) return null;
				const sel = selectedRange, min = sel?.[0], max = sel?.[1];
				const vals = (!sel || !((cur !== min) !== (cur !== max)))
					? [cur, cur + move]
					: [cur + move, cur !== min ? min! : max!];
				return vals[0] === vals[1] ? null : [Math.min(...vals), Math.max(...vals)];
			})());
		} else if (movePrime && e.ctrlKey) {
			setPrimeStation(p => {
				const idx = p ? Math.max(0, Math.min(stations.indexOf(p) + movePrime, stations.length - 1)) : movePrime < 0 ? stations.length - 1 : 0;
				if (u.cursor.idx != null)
					u.setCursor({ left: u.cursor.left!, top: u.valToPos(plotData[sidx(idx)][u.cursor.idx] ?? levels[idx], 'y') });
				u.setSeries(sidx(idx), { focus: true });
				return stations[idx];
			});
		} else if (e.code === 'KeyZ' && selectedRange) {
			u.setScale('x', { min: u.data[0][selectedRange[0]], max: u.data[0][selectedRange[1]] });
			u.setCursor({ left: -1, top: -1 });
			setCursorIdx(null);
			setSelectedRange(null);
		} else if (e.key === 'Enter') {
			setPrimeStation(focusedStation);
		} else if (e.key === 'Escape') {
			u.setScale('x', { min: u.data[0][0], max: u.data[0][u.data[0].length-1] });
			u.setCursor({ left: -1, top: -1 });
			setCursorIdx(null);
			setSelectedRange(null);
		}
	});

	const plot = useMemo(() => {
		const options = { ...size, ...plotOptions(stations, levels), hooks: {
			setLegend: [
				(upl: uPlot) => {
					const idx = upl.legend.idx;
					if (idx == null)
						return setLegend(null);
					setLegend(stations.map((s, si) =>
						({ name: s.toUpperCase().slice(0, 4), value: data[1 + si][idx], focus: (upl.series[1 + si + stations.length] as any)._focus })));
				}
			],
			setCursor: [
				(upl: any) => setCursorIdx(upl.cursor._lock ? upl.cursor.idx : null)
			],
			setScale: [
				(upl: uPlot) => setViewRange([upl.valToIdx(upl.scales.x.min!), upl.valToIdx(upl.scales.x.max!)])
			],
			setSelect: [
				(upl: uPlot) => setSelectedRange(upl.select && upl.select.width ?
					[ upl.posToIdx(upl.select.left), upl.posToIdx(upl.select.left + upl.select.width) ] : null)
			],
			setSeries: [
				(upl: any, si: any) => upl.setLegend({ idx: upl.legend.idx })
			]
		} };
		return <UplotReact {...{ options, data: plotData as any, onCreate: setUplot }}/>;
	// Size changes are done through useEffect, without reiniting whole plot
	}, [data[0][0], data[0][data[0].length-1], stations.join()]); // eslint-disable-line
	
	return (<div ref={node => setContainer(node)} style={{ position: 'absolute' }}>
		{plot}
		{legendContainer && createPortal((
			<>
				{legend && <div style={{ display: 'grid', border: '2px var(--color-border) solid', padding: '2px 4px',
					gridTemplateColumns: 'repeat(3, 120px)' }}>
					{legend.map(({ name, value, focus }) =>
						<span key={name} style={{ color: color(focus ? 'magenta' : value == null ? 'text-dark' : 'text') }}>{name}={value == null ? 'N/A' : value.toFixed(1)}</span>)}
				</div>}
			</>
		), legendContainer)}
		{focusedStation && u?.cursor.idx != null && detailsContainer && createPortal((
			<div style={{ position: 'relative', border: '2px var(--color-border) solid', width: 356, height: 240 }}>
				<MinuteView {...{ station: focusedStation, timestamp: u!.data[0][u?.cursor.idx] }}/>
			</div>
		), detailsContainer)}
	</div>);
}
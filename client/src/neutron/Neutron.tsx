import { ReactElement, Reducer, SetStateAction, createContext, useCallback, useContext, useEffect, useMemo, useReducer, useState } from 'react';
import { ManyStationsView } from './MultiView';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import { CommitMenu, FetchMenu, Help } from './Actions';
import { apiGet, apiPost, prettyDate, useEventListener } from '../util';

type Revision = {
	id: number,
	time: number,
	station: string,
	author: string | null,
	comment: string | null,
	rev_time: number[],
	rev_value: number[],
	reverted_at: number,
};
type ActionMenu = 'refetch' | 'commit' | 'help';
const STUB_VALUE = -999;

export const NeutronContext = createContext<{
	data: number[][],
	plotData: number[][],
	levels: number[],
	stations: string[],
	primeStation: string | null,
	cursorIdx: number | null,
	viewRange: number[],
	selectedRange: number[] | null,
	corrections: { [st: string]: (number | null)[] },
	showMinutes: boolean,
	openPopup: (a: SetStateAction<ActionMenu | null>) => void,
	setCursorIdx: (a: SetStateAction<number | null>) => void,
	setPrimeStation: (a: SetStateAction<string | null>) => void,
	setViewRange: (a: SetStateAction<number[]>) => void,
	setSelectedRange: (a: SetStateAction<number[] | null>) => void,
	setCorrections: (a: SetStateAction<{ [st: string]: (number | null)[] }>) => void,
	addCorrection: (station: string, fromIndex: number, values: number[]) => void
} | null>({} as any);

export default function Neutron() {
	const queryClient = useQueryClient();
	const [topContainer, setTopContainer] = useState<HTMLDivElement | null>(null);
	const [container, setContainer] = useState<HTMLDivElement | null>(null);

	const [interval, monthInput] = useMonthInput();

	const queryStations = 'all';
	const query = useQuery(['manyStations', queryStations, interval], async () => {
		const body = await apiGet('neutron/rich', {
			from: (interval[0].getTime() / 1000).toFixed(0),
			to:   (interval[1].getTime() / 1000).toFixed(0),
			stations: queryStations,
		}) as { fields: string[], corrected: any[][], revised: any[][], revisions: Revision[]  };
		if (!body?.revised.length) return null;
		console.log('neutron/rich =>', body);
		return body;
	});

	const revertMutation = useMutation((revId: number) => apiPost('neutron/revert', { id: revId }), {
		onSuccess: () => queryClient.invalidateQueries()
	});

	const [activePopup, openPopup] = useState<ActionMenu | null>(null);

	const [showMinutes, setShowMinutes] = useState(false);
	const [eff, setEff] = useState<number>(1);
	const [cursorIdx, setCursorIdx] = useState<number | null>(null);
	const [primeStation, setPrimeStation] = useState<string | null>(null);
	const [viewRange, setViewRange] = useState<number[]>([0, 0]);
	const [selectedRange, setSelectedRange] = useState<null | number[]>(null);

	const [corrections, setCorrections] = useState<{ [station: string]: (number|null)[] }>({});
	const [hoveredRev, setHoveredRev] = useState<number | null>(null);

	const partialDataState = useMemo(() => {
		if (!query.data) return null;
		const stations = query.data.fields.slice(1);
		const time = query.data.revised.map(row => row[0]);
		const uncorrectedData = stations.map((s, i) => query.data!.corrected.map(row => row[i+1]));
		const data = stations.map((s, i) => query.data!.revised
			.map((row, ri) => corrections[s]?.[ri]! < 0 ? null : corrections[s]?.[ri] ?? row[i+1]));

		const averages = data.map((sd) => {
			const s = sd.filter(v => v != null).slice().sort((a, b) => a - b), mid = Math.floor(sd.length / 2);
			return s.length % 2 === 0 ? s[mid] : (s[mid] + s[mid + 1]) / 2;
		});
		const sortedIdx = Array.from(stations.keys()).filter(i => averages[i] > 0).sort((a, b) => averages[a] - averages[b]);
		const distance = (averages[sortedIdx[sortedIdx.length-1]] - averages[sortedIdx[0]]) / sortedIdx.length;
		const spreaded = sortedIdx.map((idx, i) => data[idx].map(val => 
			val == null ? null : (val - averages[idx] - i * distance) ));
		const spreadedUnc = sortedIdx.map((idx, i) => uncorrectedData[idx].map((val, di) => 
			(val == null || val === data[idx][di]) ? null : (val - averages[idx] - i * distance) ));

		return {
			data: [time, ...sortedIdx.map(i => data[i])],
			uncorrectedData: [time, ...sortedIdx.map(i => uncorrectedData[i])],
			plotData: [time, ...spreadedUnc, ...spreaded, [], []],
			stations: sortedIdx.map(i => stations[i]),
			levels: sortedIdx.map((idx, i) => - i * distance)
		};
	}, [query.data, corrections]);

	const dataState = useMemo(() => {
		const hRev = query.data?.revisions.find(r => r.id === hoveredRev);
		if (!partialDataState) return partialDataState;
		const { data, levels, stations } = partialDataState;
		const hIindicators = Array(data[0].length).fill(null);
		if (hRev) {
			const level = levels[stations.indexOf(hRev.station)] - (levels[1] - levels[0]) / 2;
			for (const time of hRev.rev_time)
				hIindicators[data[0].indexOf(time)] = level;
		}
		let aIindicators = Array(data[0].length).fill(null);
		if (corrections) {
			for (const st in corrections) {
				const sidx = stations.indexOf(st);
				const level = levels[sidx] - (levels[1] - levels[0]) / 2;
				aIindicators = corrections[st].map(v => v == null ? null : level);
			}
		}
		return {
			...partialDataState,
			plotData: [
				...partialDataState.plotData.slice(0, -2),
				hIindicators,
				aIindicators
			]
		};
	}, [query.data, partialDataState, corrections, hoveredRev]);

	const addCorrection = useCallback((station: string, fromIndex: number, values: number[]) => {
		setCorrections(corr => {
			if (!dataState) return {};
			const sidx = dataState?.stations.indexOf(station);
			const effective = values.map((v, i) => (v === STUB_VALUE ? null : v) === dataState.data[sidx + 1][i + fromIndex] ? null : v);
			if (effective.filter(v => v != null).length < 1)
				return corr;
			const corrs = corr[station]?.slice() ?? Array(dataState.data[0].length).fill(null);
			corrs.splice(fromIndex, effective.length, ...effective);
			return { ...corr, [station]: corrs };
		});
	}, [dataState]);

	const showRevisions = (primeStation && cursorIdx && query.data?.revisions.filter(rev =>
		rev.station === primeStation && rev.rev_time.includes(dataState?.data[0][cursorIdx]))) || [];

	useEffect(() => {
		setHoveredRev(h => showRevisions.length > 0 ? h : null);
	}, [showRevisions.length]);

	// Reset corrections and other stuff when scope changes
	useEffect(() => {
		console.log('RESET');
		setCorrections({});
		setCursorIdx(null);
		setSelectedRange(null);
	}, [queryStations, interval, dataState?.data.length]);
	
	useEventListener('keydown', (e: KeyboardEvent) => {
		if (e.code === 'Escape')
			return openPopup(null);
		if (activePopup)
			return e.stopImmediatePropagation();
		if (e.code === 'KeyF') {
			openPopup('refetch');
		} else if (e.code === 'KeyC' && Object.keys(corrections).length > 0) {
			openPopup('commit');
		} else if ('KeyH' === e.code) {
			openPopup('help');
		} else if ('Delete' === e.code) {
			const fromIdx = selectedRange?.[0] ?? cursorIdx;
			if (fromIdx == null || primeStation == null) return;
			const length = selectedRange != null ? (selectedRange[1] - selectedRange[0] + 1) : 1;
			addCorrection(primeStation, fromIdx, Array(length).fill(STUB_VALUE));
		} else if ('KeyE' === e.code) {
			if (!dataState || selectedRange == null || primeStation == null) return;
			const data = dataState.data[dataState.stations.indexOf(primeStation) + 1];
			const [li, ri] = selectedRange;
			addCorrection(primeStation, li, data.slice(li, ri + 1).map(v => v / eff));
		} else if ('KeyL' === e.code) {
			queryClient.refetchQueries();
		} else if ('KeyR' === e.code) {
			setCorrections({});
		}
	});

	return (
		<NeutronContext.Provider value={dataState == null ? null : {
			...dataState,
			cursorIdx, setCursorIdx,
			primeStation, setPrimeStation,
			viewRange, setViewRange,
			selectedRange, setSelectedRange,
			corrections, setCorrections, addCorrection,
			openPopup, showMinutes
		}}>
			{activePopup && query.data && <>
				<div className='popupBackground'></div>
				<div className='popup' style={{ left: '50%', top: '45%' }}>
					<span onClick={() => openPopup(null)}
						style={{ position: 'absolute', top: 4, right: 5 }} className='closeButton'>&times;</span>
					{activePopup === 'refetch' && <FetchMenu/>}
					{activePopup === 'commit' && <CommitMenu/>}
					{activePopup === 'help' && <Help/>}
				</div>
			</>}
			<div style={{ display: 'grid', height: 'calc(100% - 6px)', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
				<div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
					<div style={{ textAlign: 'center', marginRight: 16 }}>
						[ {monthInput} ]
					</div>
					{dataState && <div style={{ margin: '0 0 4px 16px' }}>
						Primary station: <select style={{ color: primeStation ? 'var(--color-green)' : 'var(--color-text)' }} 
							value={primeStation ?? 'none'} onChange={e => setPrimeStation(e.target.value === 'none' ? null : e.target.value)}>
							<option value='none'>none</option>
							{dataState?.stations.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
						</select>
						<label>&nbsp;
							Min<input type='checkbox' checked={showMinutes} onChange={(e) => setShowMinutes(e.target.checked)}/>
						</label>
					</div>}
					{dataState && <EfficiencyInput {...{ eff, setEff }}/>}
					<div ref={node => setTopContainer(node)}></div>
					<div ref={node => setContainer(node)}></div>
					{showRevisions.length > 0 && <div style={{ maxHeight: 154, overflowY: 'scroll', border: '2px var(--color-border) solid', padding: 2 }}>
						{showRevisions.map(rev => (<div key={rev.id}
							style={{ position: 'relative', padding: '4px 0 2px 4px', backgroundColor: hoveredRev === rev.id ? 'var(--color-area)' : 'var(--color-bg)' }}
							onMouseEnter={() => setHoveredRev(rev.id)} onMouseLeave={() => setHoveredRev(null)} onBlur={() => setHoveredRev(null)}>
							<p style={{ margin: 0 }}>
								{rev.author ?? 'anon'} <span style={{ color: 'var(--color-text-dark)' }}>revised</span> [{rev.rev_time.length}] points
								<button style={{ position: 'absolute', top: 2, right: 6, padding: '0 8px' }} disabled={rev.reverted_at != null}
									onClick={() => revertMutation.mutate(rev.id)}>Revert{rev.reverted_at != null ? 'ed' : ''}</button>
							</p>
							{rev.comment ? 'Comment: '+rev.comment : ''}
							<p style={{ margin: '2px 0 0 0', fontSize: 12, color: 'var(--color-text-dark)' }}>
								at {prettyDate(new Date(rev.time*1e3))}{rev.reverted_at != null ? ' / ' + prettyDate(new Date(rev.reverted_at*1e3)) : ''}</p>
						</div>))}
					</div>}
					{Object.keys(corrections).length > 0 && <div style={{ color: 'var(--color-magenta)' }}>
						[!REV!] {Object.entries(corrections).map(([s, crr]) => `${s.toUpperCase()}:${crr.filter(c => c != null).length} `)}
					</div>}
				</div>
				<div style={{ position: 'relative', height: 'min(100%, calc(100vw / 2))', border: '2px var(--color-border) solid' }}>
					{(()=>{
						if (query.isLoading)
							return <div className='center'>LOADING...</div>;
						if (query.isError)
							return <div className='center' style={{ color: 'var(--color-red)' }}>FAILED TO LOAD</div>;
						if (!query.data)
							return <div className='center'>NO DATA</div>;
						return <ManyStationsView {...{ legendContainer: topContainer, detailsContainer: container }}/>;
					})()}
				</div>
			</div>
			<button style={{ position: 'fixed', left: 4, bottom: 8, height: 24, width: 24, padding: 0, border: '1px var(--color-border) solid' }}
				onClick={() => openPopup('help')}>?</button>
		</NeutronContext.Provider>);
}

const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export function useMonthInput() {
	type R = Reducer<{ year: number, month: number, count: number, interval: Date[]}, { action: 'month'|'year'|'count', value: number }>;
	const [{ year, month, count, interval }, dispatch] = useReducer<R>((state, { action, value }) => {
		const st = { ...state, [action]: value };
		st.interval = [0, st.count].map(inc => new Date(Date.UTC(st.year, st.month + inc)));
		return st;
	}, {
		year: new Date().getFullYear(),
		month: new Date().getMonth(),
		count: 1,
		interval: [0, 1].map(inc => new Date(Date.UTC(new Date().getFullYear(), new Date().getMonth() + inc)))
	});
	const set = (action: 'month'|'year'|'count', value: number) => dispatch({ action, value });

	return [interval, <div style={{ display: 'inline-block' }}>
		<select onWheel={e => set('month', Math.max(0, Math.min(month + Math.sign(e.deltaY), 11)))}
			value={monthNames[month]} onChange={e => set('month', monthNames.indexOf(e.target.value))}>
			{monthNames.map(mon => <option key={mon} id={mon}>{mon}</option>)}
		</select> <input style={{ width: '6ch' }} type='number' min='1957' max={new Date().getFullYear()}
			value={year} onChange={e => set('year', e.target.valueAsNumber)}
		/> + <input style={{ width: '4ch', textAlign: 'center' }} type='number' min='1' max='24'
			value={count} onChange={e => set('count', e.target.valueAsNumber)}
		/> month{count === 1 ? '' : 's'}
	</div>] as [Date[], ReactElement];
}

const defaultDivisor = 18;  // TODO: smart divisor determination
function EfficiencyInput({ eff, setEff }: { eff: number, setEff: (a: number) => void }) {
	const { data: allData, selectedRange, primeStation, stations } = useContext(NeutronContext)!;

	type R = Reducer<{ text: string, value: number, div: number|null }, { action: 'value'|'div'|'checkbox'|'auto', value?: any }>;
	const [ { text, value, div }, dispatch ] = useReducer<R>((st, { action, value: aValue }) => {
		if (action === 'value') {
			const val = parseFloat(aValue);
			return { text: aValue, value: isNaN(val) ? st.value : val, div: st.div };
		} if (action === 'div') {
			const val = st.value / (st.div || 1) * (aValue as number);
			return { text: (Math.round(1000 * val) / 1000).toString(), value: val, div: aValue };
		} else if (action === 'checkbox') {
			const val = aValue ? (st.value * defaultDivisor) : st.value / (st.div || 1);
			return { text: (Math.round(1000 * val) / 1000).toString(), value: val, div: aValue ? defaultDivisor : null };
		} else {
			if (!selectedRange || !primeStation)
				return st;
			const data = allData[stations.indexOf(primeStation) + 1];
			const [li, ri] = selectedRange; // left - lval 
			const left = data.slice(0, li).findLast(v => v != null);
			const right = data.slice(ri + 1).find(v => v != null);
			if (left == null || right == null)
				return st;
			const lEff = data[li] / left, rEff = data[ri] / right;
			const efficiency = (lEff + rEff) / 2;
			const val = efficiency * (st.div || 1);
			return { text: (Math.round(1000 * val) / 1000).toString(), value: val, div: st.div };
		}
	}, {
		text: eff.toFixed(1),
		value: eff,
		div: null
	});

	useEffect(() => setEff(value / (div || 1)), [value, div, setEff]); // FIXME: ehh

	useEventListener('keydown', (e: KeyboardEvent) => {
		if (e.code === 'KeyA')
			dispatch({ action: 'auto' });
	});

	return (<div style={{ display: 'inline-block' }}>
		<label> Div<input type='checkbox' onChange={(e) => dispatch({ action: 'checkbox', value: e.target.checked })}/> </label>
		Eff=
		<input style={{ width: '6ch', borderColor: 'var(--color-border)', textAlign: 'center' }}
			type='text' value={text} onChange={(e) => dispatch({ action: 'value', value: e.target.value })}/>
		{div != null && <span>&nbsp;/ <input style={{ width: '6ch', borderColor: 'var(--color-border)', textAlign: 'center' }}
			type='number' step={1} value={div.toFixed(0)}
			onChange={(e) => dispatch({ action: 'div', value: e.target.valueAsNumber })}/></span>}
		<button style={{ marginLeft: 24, padding: '1px 16px' }} disabled={!selectedRange || !primeStation}
			onClick={()=>dispatch({ action: 'auto' })}>AUTO</button>
	</div>);
}
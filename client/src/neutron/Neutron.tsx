import { SetStateAction, createContext, useEffect, useMemo, useState } from 'react';
import { ManyStationsView } from './MultiView';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import { CommitMenu, FetchMenu } from './Actions';
import { prettyDate, useEventListener } from '../util';

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
type ActionMenu = 'refetch' | 'commit';
const STUB_VALUE = -999;
const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

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
	openPopup: (a: SetStateAction<ActionMenu | null>) => void,
	setCursorIdx: (a: SetStateAction<number | null>) => void,
	setPrimeStation: (a: SetStateAction<string | null>) => void,
	setViewRange: (a: SetStateAction<number[]>) => void,
	setSelectedRange: (a: SetStateAction<number[] | null>) => void,
	setCorrections: (a: SetStateAction<{ [st: string]: (number | null)[] }>) => void,
} | null>({} as any);

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
		const body = await res.json() as { fields: string[], corrected: any[][], revised: any[][], revisions: Revision[]  };
		if (!body?.revised.length) return null;
		console.log(path, '=>', body);
		return body;
	};
}

export default function Neutron() {
	const queryClient = useQueryClient();
	const [topContainer, setTopContainer] = useState<HTMLDivElement | null>(null);
	const [container, setContainer] = useState<HTMLDivElement | null>(null);

	const [year, setYear] = useState(new Date().getFullYear());
	const [month, setMonth] = useState(new Date().getMonth());
	const [monthCount, setMonthCount] = useState(1);
	const interval = [0, monthCount].map(inc => new Date(Date.UTC(year, month + inc))) as [Date, Date];

	const queryStations = 'all';
	const query = useQuery(['manyStations', queryStations, interval], queryFunction('api/neutron/rich', interval, [queryStations]));

	const revertMutation = useMutation(async (revId: number) => {
		const res = await fetch(process.env.REACT_APP_API + 'api/neutron/revert', {
			method: 'POST', credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ id: revId })
		});
		if (res.status !== 200)
			throw Error('HTTP '+res.status);
		return await res.text();
	}, {
		onSuccess: () => queryClient.invalidateQueries()
	});

	const [activePopup, openPopup] = useState<ActionMenu | null>(null);

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
			plotData: [time, ...spreadedUnc, ...spreaded, []],
			stations: sortedIdx.map(i => stations[i]),
			levels: sortedIdx.map((idx, i) => - i * distance)
		};
	}, [query.data, corrections]);

	const dataState = useMemo(() => {
		const rev = query.data?.revisions.find(r => r.id === hoveredRev);
		if (!partialDataState || !rev) return partialDataState;
		const { data, levels, stations } = partialDataState;
		const indicators = Array(data[0].length).fill(null);
		const level = levels[stations.indexOf(rev.station)] - (levels[1] - levels[0]) / 2;
		for (const time of rev.rev_time)
			indicators[data[0].indexOf(time)] = level;
		return {
			...partialDataState,
			plotData: [...partialDataState.plotData.slice(0, -1), indicators]
		};
	}, [query.data, partialDataState, hoveredRev]);

	const addCorrection = (station: string, fromIndex: number, values: number[]) => {
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
	};

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
	}, [queryStations, year, month, monthCount, dataState?.data.length]);
	
	useEventListener('keydown', (e: KeyboardEvent) => {
		if (e.code === 'KeyF')
			openPopup('refetch');
		if (e.code === 'KeyC' && Object.keys(corrections).length > 0)
			openPopup('commit');
		else if (e.code === 'Escape')
			openPopup(null);
		if (activePopup)
			return e.stopImmediatePropagation();
		if ('Delete' === e.code) {
			const fromIdx = selectedRange?.[0] ?? cursorIdx;
			if (fromIdx == null || primeStation == null) return;
			const length = selectedRange != null ? (selectedRange[1] - selectedRange[0] + 1) : 1;
			addCorrection(primeStation, fromIdx, Array(length).fill(STUB_VALUE));
		} else if ('KeyL' === e.code) {
			queryClient.invalidateQueries();
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
			corrections, setCorrections,
			openPopup
		}}>
			{activePopup && query.data && <>
				<div className='popupBackground'></div>
				<div className='popup' style={{ left: '50%', top: '45%' }}>
					<span onClick={() => openPopup(null)}
						style={{ position: 'absolute', top: 4, right: 5 }} className='closeButton'>&times;</span>
					{activePopup === 'refetch' && <FetchMenu/>}
					{activePopup === 'commit' && <CommitMenu/>}
				</div>
			</>}
			<div style={{ display: 'grid', height: 'calc(100% - 6px)', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
				<div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
					<div style={{ textAlign: 'center', marginRight: 16 }}>
						[ <select onWheel={e => setMonth(m => Math.max(0, Math.min(m + Math.sign(e.deltaY), 11)))}
							value={monthNames[month]} onChange={e => setMonth(monthNames.indexOf(e.target.value))}>
							{monthNames.map(mon => <option key={mon} id={mon}>{mon}</option>)}
						</select> <input style={{ width: '6ch' }} type='number' min='1957' max={new Date().getFullYear()}
							value={year} onChange={e => setYear(e.target.valueAsNumber)}
						/> + <input style={{ width: '3ch' }} type='number' min='1' max='24' value={monthCount} onChange={e => setMonthCount(e.target.valueAsNumber)}
						/> month{monthCount === 1 ? '' : 's'} ]
					</div>
					{query.data && <div style={{ margin: '0 0 4px 16px' }}>
						Primary station: <select style={{ color: primeStation ? 'var(--color-green)' : 'var(--color-text)' }} 
							value={primeStation ?? 'none'} onChange={e => setPrimeStation(e.target.value === 'none' ? null : e.target.value)}>
							<option value='none'>none</option>
							{dataState?.stations.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
						</select>
					</div>}
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
						return <ManyStationsView {...{ interval, legendContainer: topContainer, detailsContainer: container }}/>;
					})()}
				</div>
			</div>
		</NeutronContext.Provider>);
}
import { SetStateAction, createContext, useState } from 'react';
import { ManyStationsView } from './MultiView';
import { useQuery } from 'react-query';
import { FetchMenu } from './Actions';
import { useEventListener } from '../util';

type ActionMenu = 'refetch';
const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const NeutronContext = createContext<{
	data: number[][],
	plotData: number[][],
	levels: number[],
	stations: string[],
	primeStation: string | null,
	setPrimeStation: (a: SetStateAction<string | null>) => void,
	viewRange: number[],
	setViewRange: (a: SetStateAction<number[]>) => void,
	selectedRange: number[] | null,
	setSelectedRange: (a: SetStateAction<number[] | null>) => void,
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

export default function Neutron() {
	const [year, setYear] = useState(new Date().getFullYear());
	const [month, setMonth] = useState(new Date().getMonth());
	const [monthCount, setMonthCount] = useState(1);
	const interval = [0, monthCount].map(inc => new Date(Date.UTC(year, month + inc))) as [Date, Date];

	const queryStations = ['all'];
	const query = useQuery(['manyStations', queryStations, interval], queryFunction('api/neutron', interval, queryStations));

	const [activePopup, openPopup] = useState<ActionMenu | null>(null);

	const [primeStation, setPrimeStation] = useState<string | null>(null);
	const [viewRange, setViewRange] = useState<number[]>([0, 0]);
	const [selectedRange, setSelectedRange] = useState<null | number[]>(null);

	const [topContainer, setTopContainer] = useState<HTMLDivElement | null>(null);
	const [container, setContainer] = useState<HTMLDivElement | null>(null);

	useEventListener('keydown', (e: KeyboardEvent) => {
		if (activePopup)
			e.stopImmediatePropagation();
		if (e.code === 'KeyF')
			openPopup('refetch');
		else if (e.code === 'Escape')
			openPopup(null);
	});
	console.log(viewRange)
	return (
		<NeutronContext.Provider value={query.data == null ? null : {
			...query.data,
			primeStation, setPrimeStation,
			viewRange, setViewRange,
			selectedRange, setSelectedRange
		}}>
			{activePopup && query.data && <>
				<div className='popupBackground'></div>
				<div className='popup' style={{ left: '50%', top: '45%' }}>
					<span onClick={() => openPopup(null)}
						style={{ position: 'absolute', top: 4, right: 5 }} className='closeButton'>&times;</span>
					<FetchMenu/>
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
							{query.data.stations.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
						</select>
					</div>}
					<div ref={node => setTopContainer(node)}></div>
					<div ref={node => setContainer(node)}></div>
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
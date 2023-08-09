import { useRef, useState } from 'react';
import { ManyStationsView } from './MultiView';

const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export default function Neutron() {
	const [year, setYear] = useState(new Date().getFullYear());
	const [month, setMonth] = useState(new Date().getMonth());
	const [monthCount, setMonthCount] = useState(1);
	const interval = [0, monthCount].map(inc => new Date(Date.UTC(year, month + inc))) as [Date, Date];

	const [topContainer, setTopContainer] = useState<HTMLDivElement | null>(null);
	const [container, setContainer] = useState<HTMLDivElement | null>(null);

	return <div style={{ display: 'grid', height: 'calc(100% - 6px)', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
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
			<div ref={node => setTopContainer(node)}></div>
			<div ref={node => setContainer(node)}></div>
		</div>
		<div style={{ position: 'relative', height: 'min(100%, calc(100vw / 2))', border: '2px var(--color-border) solid' }}>
			<ManyStationsView {...{ interval, legendContainer: topContainer }}/>
		</div>
	</div>;
}
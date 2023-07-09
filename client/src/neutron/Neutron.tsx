import { useState } from 'react';
import { ManyStationsView } from './MultiView';

const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export default function Neutron() {
	const [year, setYear] = useState(new Date().getFullYear());
	const [month, setMonth] = useState(new Date().getMonth());
	const [monthCount, setMonthCount] = useState(1);
	const interval = [0, monthCount].map(inc => new Date(Date.UTC(year, month + inc))) as [Date, Date];

	return <div>
		<div>
			Date:
			<select style={{ margin: '0 1ch' }} value={monthNames[month]} onChange={e => setMonth(monthNames.indexOf(e.target.value))}>
				{monthNames.map(mon => <option key={mon} id={mon}>{mon}</option>)}
			</select>
			<input style={{ width: '6ch' }} type='number' min='1957' max={new Date().getFullYear()}
				value={year} onChange={e => setYear(e.target.valueAsNumber)}
			/> + <input style={{ width: '3ch' }} type='number' min='1' max='24' value={monthCount} onChange={e => setMonthCount(e.target.valueAsNumber)}
			/> month{monthCount === 1 ? '' : 's'}
		</div>
		<ManyStationsView interval={interval}/>
	</div>;
}
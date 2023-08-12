import { useContext } from 'react';
import { prettyDate } from '../util';
import { NeutronContext } from './Neutron';

export function FetchMenu() {
	const { stations, primeStation, viewInterval: interval } = useContext(NeutronContext)!;
	return (<div>
		<h4 style={{ margin: '1em 0 1.5em 0' }}>Re-obtain and re-compute data?</h4>
		<p style={{ margin: '1em 3em 2em 3em', textAlign: 'right', lineHeight: '1.5em' }}>
			<b>{Math.ceil((interval[1] - interval[0]) / 3600)}</b> hours<br/>
			from {prettyDate(new Date(1e3*interval[0]))}<br/>
			to {prettyDate(new Date(1e3*interval[1]))}<br/>
		</p>
		<button style={{ padding: '2px 16px' }} disabled={primeStation == null}>Fetch {primeStation?.toUpperCase() ?? '???'}</button>
		<button style={{ padding: '2px 16px', marginLeft: 24 }}>Fetch all</button>
	</div>);
}
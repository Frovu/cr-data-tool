import { prettyDate } from '../util';

export function Fetch({ stations, primeStation, interval }:
{ stations: string[], primeStation: string | null, interval: [number, number] }) {
	return (<div>
		<h4>Re-obtain and recompute?</h4>
		{Math.ceil((interval[1] - interval[0]) / 3600)} hours<br/>
		from {prettyDate(new Date(1e3*interval[0]))}<br/>
		to {prettyDate(new Date(1e3*interval[1]))}<br/>
		<button disabled={primeStation == null}>Fetch {primeStation ?? '???'}</button>
		<button>Fetch all</button>
	</div>);
}
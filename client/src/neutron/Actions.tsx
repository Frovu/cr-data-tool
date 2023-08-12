import { useContext, useState } from 'react';
import { prettyDate } from '../util';
import { NeutronContext } from './Neutron';
import { useMutation, useQueryClient } from 'react-query';

export function FetchMenu() {
	const queryClient = useQueryClient();
	const { stations, data: neutronData, primeStation, viewRange, selectedRange } = useContext(NeutronContext)!;
	const interval = (selectedRange ?? viewRange).map(v => neutronData[0][v]);

	const [report, setReport] = useState('');

	const mutation = useMutation(async (stationQuery: string[]) => {
		const urlPara = new URLSearchParams({
			from: interval[0].toFixed(0),
			to:   interval[1].toFixed(0),
			stations: stationQuery.join(),
		}).toString();
		const res = await fetch(process.env.REACT_APP_API + 'api/neutron/refetch?' + urlPara);
		if (res.status !== 200)
			throw Error('HTTP '+res.status);
		const body = await res.json() as { duration: number, changeCounts: {[station: string]: number} };
		console.log('refetch => ', body);
		return body;
	}, {
		onError: (e: any) => setReport(e.toString()),
		onSuccess: (data) => {
			queryClient.invalidateQueries();
			setReport(`Done in ${data.duration.toFixed(1)} seconds\n`
				+ Object.entries(data.changeCounts).map(([st, n]) => `${st.toUpperCase()}: ${n}`).join('\n'));
		}
	});

	return (<div>
		<h4 style={{ margin: '1em 0 1.5em 0' }}>Re-obtain and re-compute data?</h4>
		<p style={{ margin: '1em 3em 0 3em', textAlign: 'right', lineHeight: '1.5em' }}>
			<b>{Math.ceil((interval[1] - interval[0]) / 3600) + 1}</b> hours<br/>
			from {prettyDate(new Date(1e3*interval[0]))}<br/>
			to {prettyDate(new Date(1e3*interval[1]))}<br/>
		</p>
		<pre style={{ color: mutation.isError ? 'var(--color-red)' :  mutation.isLoading ? 'var(--color-text)' : 'var(--color-green)' }}>
			{mutation.isLoading ? 'loading..' : report}
		</pre>
		<button style={{ padding: '2px 16px' }} disabled={mutation.isLoading || primeStation == null} autoFocus={primeStation != null}
			onClick={()=>mutation.mutate([primeStation!])}>Fetch {primeStation?.toUpperCase() ?? '???'}</button>
		<button style={{ padding: '2px 16px', marginLeft: 24 }} disabled={mutation.isLoading}
			onClick={()=>mutation.mutate(stations)}>Fetch all</button>
	</div>);
}
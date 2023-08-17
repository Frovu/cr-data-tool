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
		const res = await fetch(process.env.REACT_APP_API + 'api/neutron/refetch?' + urlPara, { credentials: 'include' });
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

export function CommitMenu() {
	const queryClient = useQueryClient();

	const { data, corrections: allCorrs, setCorrections, openPopup } = useContext(NeutronContext)!;

	const [comment, setComment] = useState('');
	const [report, setReport] = useState('');

	const corrections = Object.fromEntries(Object.entries(allCorrs)
		.map(([sta, values]) => [sta,
			values.map((v, i) => v == null ? null : [data[0][i], v]).filter((ch): ch is number[] => ch != null)]));

	const mutation = useMutation(async () => {
		const res = await fetch(process.env.REACT_APP_API + 'api/neutron/revision', {
			method: 'POST', credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ comment: comment || null, revisions: corrections })
		});
		if (res.status !== 200)
			throw Error('HTTP '+res.status);
		return await res.text();
	}, {
		onError: (e: any) => setReport(e.toString()),
		onSuccess: () => {
			queryClient.invalidateQueries();
			openPopup(p => p !== 'commit' ? p : null);
			setCorrections({});
		}
	});

	return (<div>
		<h4 style={{ margin: '1em 0 1.5em 0' }}>Commit revisions?</h4>
		<div style={{ margin: '1em 3em 0 3em', textAlign: 'right', lineHeight: '1.25em' }}>
			{Object.entries(corrections).map(([sta, corrs]) =>
				<p key={sta} style={{ margin: '1em 0 0 0' }}>
					<span style={{ color: 'var(--color-magenta)' }}>[{sta.toUpperCase()}]</span> <b>{corrs.length} </b>
					change{corrs.length === 1 ? '' : 's'} between&nbsp;
					{prettyDate(new Date(1e3*corrs[0][0]))}<br/> and {prettyDate(new Date(1e3*corrs[corrs.length-1][0]))} </p>)}
		</div>
		<pre style={{ margin: 4, height: '1.25em', color: mutation.isError ? 'var(--color-red)' :  mutation.isLoading ? 'var(--color-text)' : 'var(--color-green)' }}>
			{mutation.isLoading ? 'loading..' : report}
		</pre>
		<div><input type='text' placeholder='Comment' value={comment} onChange={(e) => setComment(e.target.value)}
			style={{ padding: 4, margin: 8, width: 360, borderColor: 'var(--color-border)' }}></input></div>
		<button style={{ padding: '2px 24px' }} autoFocus disabled={mutation.isLoading} onClick={()=>mutation.mutate()}>COMMIT</button>
		<button style={{ padding: '2px 24px', marginLeft: 24 }} onClick={() => openPopup(null)}>CANCEL</button>
	</div>);
}

export function Help() {
	return (<div style={{ width: '64vw' }}>
		<h4>How it (should) work</h4>
		<p style={{ textAlign: 'left', margin: '0 2em' }}>
			Use arrow keys to move cursor. Press ctrl/alt to get more speed.<br/>
			Use shift to select regions with keyborad.<br/>
			Use ctrl + up/down keys to change prime station.<br/>
			Use double-click to select prime station from plot.<br/>
			Drag cursor with shift/ctrl to zoom.<br/>
			Press enter to make focused station prime.<br/>
			Revisions log regarding point of fixed cursor is listed below minute plot.<br/>
			Enable "Div" mode to input efficiency as a rational number (much better when n/18 counters are broke)<br/>
			On a minute plot drag cursor with shift pressed to apply mask. Green line means current value of this hour, orange - automatically computed, yellow - computed with the mask. Press <b>I</b> for this to take effect.<br/>
		</p>
		<h4 style={{ textAlign: 'left' }}>Keys to know</h4>
		<p style={{ textAlign: 'left', margin: '0 2em' }}>
			<b>H</b> - View this sacred message<br/>
			<b>F</b> - Refetch data from source<br/>
			<b>Z</b> - Zoom plot into selection<br/>
			<b>R</b> - Discard not commited corrections<br/>
			<b>C</b> - Commit corrections<br/>
			<b>A</b> - Automatically determine efficieny from selection<br/>
			<b>I</b> - Integrate current hour with a mask applied<br/>
			<b>E</b> - Correct for efficiency<br/>
			<b>Del</b> - Correct by removing points<br/>
			<b>Esc</b> - To break free<br/>
		</p>
	</div>);
}
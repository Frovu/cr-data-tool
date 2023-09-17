import { useMemo, useState } from 'react';
import { apiGet, apiPost, prettyDate, useMonthInput } from '../util';
import { NavigatedPlot, NavigationContext, useNavigationState, axisDefaults, seriesDefaults, color } from '../plotUtil';
import { useMutation, useQuery } from 'react-query';
import uPlot from 'uplot';

function options(): Omit<uPlot.Options, 'width'|'height'> {
	return {
		padding: [12, 12, 0, 8],
		scales: {
			temp: {
				range: (u, min, max) => [min-(max-min)*2, max+1]
			},
			press: {
				range: (u, min, max) => [min-(max-min)*2, max+1]
			},
			variation: {
				range: (u, min, max) => [min-.1, max*3/2]
			}
		},
		axes: [
			{
				...axisDefaults(),
			}, {
				...axisDefaults(),
				scale: 'temp'
			}, {
				...axisDefaults(),
				scale: 'temp'
			}, {
				...axisDefaults(),
				scale: 'temp'
			}
		],
		series: [
			{
				value: '{YYYY}-{MM}-{DD} {HH}:{mm} UTC',
				stroke: color('text')
			},
			{
				...seriesDefaults('t_m_avg', 'green', 't'),
				value: (u, val) => val?.toFixed(1) ?? '--',
				width: 2,
			},
		]
	};
}

export default function MuonApp() {
	const [interval, monthInput] = useMonthInput(new Date(Date.now() - 864e5*365), 12);
	const [experiment, setExperiment] = useState('Moscow-pioneer');
	const navigation = useNavigationState();

	const query = useQuery({
		queryKey: ['muon', interval],
		queryFn: () => apiGet<{ fields: string[], rows: number[][] }>('muon', {
			from: interval[0],
			to: interval[1],
			experiment,
			query: 'pressure,t_mass_average,original,corrected,revised'
		})
	});

	const data = useMemo(() => {
		if (!query.data) return null;
		const transposed = query.data.fields.map((f, i) => query.data.rows.map(row => row[i]));
		return transposed[0].length < 2 ? null : transposed;
	}, [query.data]);

	const { min, max } = (navigation.state.selection ?? navigation.state.view);
	const [fetchFrom, fetchTo] = (!data || (min === 0 && max === data[0].length - 1))
		? interval : [min, max].map(i => data[0][i]);

	type mutResp = { status: 'busy'|'ok'|'error', downloading?: { [key: string]: number }, message?: string };
	const obtainMutation = useMutation(() => apiPost<mutResp>('muon/obtain', {
		from: fetchFrom,
		to: fetchTo,
		experiment
	}), {
		onSuccess: ({ status }) => {
			if (status === 'busy')
				setTimeout(() => obtainMutation.mutate(), 500);
			else 
				setTimeout(() => obtainMutation.isSuccess && obtainMutation.reset(), 3000);
		}
	});

	const isObtaining = obtainMutation.isLoading || (obtainMutation.isSuccess && obtainMutation.data.status === 'busy');
	return <NavigationContext.Provider value={navigation}>
		<div style={{ height: '100%', display: 'grid', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
			<div>
				{monthInput}
				<div style={{ padding: '8px 0 0 8px' }}>
					Experiment: {experiment}
				</div>
				<div style={{ color: color('red'), padding: 8 }}>{query.error?.toString()}</div>
				<div style={{ padding: 8 }}>
					<div style={{ color: color('text'), paddingBottom: 16, verticalAlign: 'top' }}>
							[{Math.ceil((fetchTo - fetchFrom) / 3600)} h]
						<div style={{ display: 'inline-block', color: color('text-dark'), textAlign: 'right', lineHeight: 1.25 }}>
							{prettyDate(fetchFrom)}<br/>
							&nbsp;&nbsp;to {prettyDate(fetchTo)}
						</div>
					</div>
					<div>
						<button style={{ padding: 2, width: 196 }} disabled={isObtaining} onClick={() => obtainMutation.mutate()}>
							{isObtaining ? 'stand by...' : 'Obtain everything'}</button>
						<button style={{ padding: 2, marginTop: 4, width: 196 }} disabled={isObtaining} onClick={() => obtainMutation.mutate()}>
							{isObtaining ? 'stand by...' : 'Obtain only counts'}</button>
						{obtainMutation.data?.status === 'ok' && <span style={{ paddingLeft: 8, color: color('green') }}>OK</span>}
					</div>
					{/* <button style={{ padding: '2px 12px' }} onClick={() => computeMutation.mutate()}>Compute</button> */}
					<div style={{ paddingTop: 4 }}>
						<div>{(obtainMutation.data?.status === 'busy' && obtainMutation.data?.message)}</div>
						{Object.entries(obtainMutation.data?.downloading ?? {}).map(([year, progr]) => <div key={year}>
							downloading {year}: <span style={{ color: color('acid') }}>{(progr * 100).toFixed(0)} %</span>
						</div>)}
						<div style={{ color: color('red') }}>{obtainMutation.error?.toString() ??
							(obtainMutation.data?.status === 'error' && obtainMutation.data?.message)}</div>
					</div>
				</div>
			</div>
			<div style={{ position: 'relative' }}>
				{query.isLoading && <div className='center'>LOADING...</div>}
				{query.data && !data && <div className='center'>NO DATA</div>}
				{data && <NavigatedPlot {...{ data, options }}/>}
			</div>
		</div>
	</NavigationContext.Provider>;
}
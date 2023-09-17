import { useMemo, useState } from 'react';
import { apiGet, useMonthInput } from '../util';
import { NavigatedPlot, NavigationContext, useNavigationState, axisDefaults, seriesDefaults, color } from '../plotUtil';
import { useQuery } from 'react-query';
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
		return [];
	}, [query.data]);

	return <NavigationContext.Provider value={navigation}>
		<div style={{ height: '100%', display: 'grid', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
			<div>
				{monthInput}
				<div style={{ padding: '8px 0 0 8px' }}>
					Experiment: {experiment}
				</div>
				<div style={{ color: color('red'), padding: 8 }}>{query.error?.toString()}</div>
			</div>
			<div style={{ position: 'relative' }}>
				{query.isLoading && <div className='center'>LOADING...</div>}
				{query.data && !data?.length && <div className='center'>NO DATA</div>}
				{data && data.length > 0 && <NavigatedPlot {...{ data, options }}/>}
			</div>
		</div>
	</NavigationContext.Provider>;
}
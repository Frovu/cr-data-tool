import { useQuery } from 'react-query';
import { NavigationContext, color, useNavigationState, axisDefaults, seriesDefaults } from '../plotUtil';
import { apiGet, useMonthInput, useSize } from '../util';
import { useEffect, useMemo, useState } from 'react';
import UplotReact from 'uplot-react';
import uPlot from 'uplot';

const LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20, 10];

function plotOptions(): Omit<uPlot.Options,'width'|'height'> {
	return {
		legend: { show: false },
		padding: [12, 12, 0, 8],
		cursor: {
			drag: { y: true },
			points: { fill: color('text') }
		},
		scales: {
			t: {
				range: (u, min, max) => [min-1, max+1]
			}
		},
		axes: [
			{
				...axisDefaults(),
			}, {
				...axisDefaults(),
				scale: 't'
			}
		],
		series: [
			{ value: '{YYYY}-{MM}-{DD} {HH}:{mm}', stroke: color('text') },
			{
				...seriesDefaults('t_m', 'green', 't'),
				width: 2,
			},
			...LEVELS.map(lvl => ({
				...seriesDefaults(`t_${lvl}mb`, 'purple', 't'),
			}))
		]

	};
}

export default function TemperatureApp() {
	const [interval, monthInput] = useMonthInput(new Date(Date.now() - 864e5 * 30));
	const navigation = useNavigationState();

	const query = useQuery({
		queryKey: ['temperature', interval],
		queryFn: () => apiGet<{ status: 'ok' | 'busy', downloading?: { [key: string]: number },
			fields: string[], rows: number[][] }>('temperature', {
			from: interval[0],
			to: interval[1],
			lat: 55.47,
			lon: 37.32,
		}),
		refetchInterval: (data) => data?.status === 'busy' ? 500 : false
	});

	const [container, setContainer] = useState<HTMLDivElement | null>(null);
	const [u, setUplot] = useState<uPlot | null>(null);
	const size = useSize(container);

	useEffect(() => u?.setSize(size), [u, size]);

	const plotComponent = useMemo(() => {
		if (!query.data) return null;
		const { status, rows, fields } = query.data;
		if (status !== 'ok') return null;

		const data = fields.map((f, i) => rows.map(row => row[i]));

		return <UplotReact {...{ options: { ...size, ...plotOptions() }, data: data as any, onCreate: setUplot }}/>;
	}, [query.data]); // eslint-disable-line

	return <NavigationContext.Provider value={navigation}>
		<div style={{ height: '100%', display: 'grid', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
			<div>
				{monthInput}
				<div style={{ padding: 12 }}>
					<div>status: {query.data?.status}</div> 
					{Object.entries(query.data?.downloading ?? {}).map(([year, progr]) => <div key={year}>
						downloading {year}: {(progr * 100).toFixed(0)} %
					</div>)}
				</div>
			</div>
			<div ref={el => setContainer(el)} style={{ position: 'relative' }}>
				<div style={{ position: 'absolute' }}>
					{plotComponent}
				</div>
			</div>

		</div>
	</NavigationContext.Provider>;
}
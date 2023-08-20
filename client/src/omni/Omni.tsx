import { useMutation, useQuery, useQueryClient } from 'react-query';
import { useMonthInput } from '../neutron/Neutron';
import { apiGet } from '../util';
import uPlot from 'uplot';
import { NavigationState, NavigatedPlot, NavigationContext, color, font, useNavigationState } from '../plotUtil';
import { useMemo, useState } from 'react';

function plotOptions(): Omit<uPlot.Options, 'height'|'width'> {
	return {
		axes: [
			{
				font: font(14),
				stroke: color('text'),
				grid: { show: true, stroke: color('grid'), width: 2 },
				ticks: { stroke: color('grid'), width: 2 },
			}, {
				scale: 'imf',
				font: font(12),
				stroke: color('text'),
				grid: { show: true, stroke: color('grid'), width: 2 },
				ticks: { stroke: color('grid'), width: 2 },
			}
		],
		series: [
			{ value: '{YYYY}-{MM}-{DD} {HH}:{mm}', stroke: color('text') },
			{
				label: 'Vsw',
				stroke: color('acid'),
				points: { fill: color('bg'), stroke: color('acid') }
			}, {
				scale: 'imf',
				label: 'Imf',
				stroke: color('purple'),
				points: { fill: color('bg'), stroke: color('purple') }
			}
		]
	};
}

export function Omni() {
	const [interval, monthInput] = useMonthInput(new Date(Date.now() - 864e5 * 60));

	const query = useQuery<{ fields: string[], rows: number[][] }>(['omni', interval], () => apiGet('omni', {
		from: Math.floor(interval[0].getTime() / 1e3),
		to:   Math.floor(interval[1].getTime() / 1e3),
		query: 'sw_speed,imf_scalar'
	}));

	const navigation = useNavigationState();
	const data = useMemo(() => {
		return query.data?.fields.map((f, i) => query.data.rows.map(r => r[i]));
	}, [query.data]);

	return (<div style={{ display: 'grid', height: 'calc(100% - 6px)', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
		<NavigationContext.Provider value={navigation}>
			<div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
				<div style={{ textAlign: 'center', marginRight: 16 }}>
					[ {monthInput} ]
				</div>
			</div>
			<div style={{ position: 'relative', height: 'min(100%, calc(100vw / 2))', border: '2px var(--color-border) solid' }}>
				{(()=>{
					if (query.isLoading)
						return <div className='center'>LOADING...</div>;
					if (query.isError)
						return <div className='center' style={{ color: 'var(--color-red)' }}>FAILED TO LOAD</div>;
					if (!query.data)
						return <div className='center'>NO DATA</div>;
					return <NavigatedPlot {...{ data: data!, options: plotOptions }}/>;
				})()}
			</div>
		</NavigationContext.Provider>
	</div>);
}
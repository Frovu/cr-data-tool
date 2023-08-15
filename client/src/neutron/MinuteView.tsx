import { useQuery } from 'react-query';
import uPlot from 'uplot';
import { color, font } from '../plotUtil';
import UplotReact from 'uplot-react';
import { prettyDate } from '../util';

export default function MinuteView({ timestamp, station: queryStation }: { timestamp: number, station: string }) {
	const query = useQuery({
		queryKey: ['minuteView', timestamp, queryStation],
		keepPreviousData: true,
		queryFn: async () => {
			const urlPara = new URLSearchParams({
				timestamp: timestamp.toString(),
				station: queryStation
			}).toString();
			const res = await fetch(process.env.REACT_APP_API + 'api/neutron/minutes?' + urlPara);
			if (res.status !== 200)
				throw Error('HTTP '+res.status);
			const body = await res.json() as { station: string, raw: number[], filtered: number[], integrated: number };
			// console.log('minutes => ', body);
			return body;
		}
	});

	if (query.isLoading)
		return <div className='center'>LOADING..</div>;
	if (query.isError)
		return <div className='center' style={{ color: color('red') }}>FAILED TO LOAD</div>;
	if (!query.data)
		return <div className='center'>NO DATA</div>;

	const options = {
		width: 356, height: 240,
		legend: { show: false },
		padding: [8, 8, 0, 0],
		cursor: {
			points: {
				size: 6,
				fill: color('acid'),
				stroke: color('acid')
			},
			drag: { dist: 10, y: true }
		},
		scales: {
			x: { time: false },
			y: {
				range: (u, min, max) =>  [min - 2, max + 2]
			}
		},
		axes: [
			{
				size: 34,
				font: font(12),
				stroke: color('text'),
				grid: { show: true, stroke: color('grid'), width: 2 },
				ticks: { stroke: color('grid'), width: 2 },
				values: (u, vals) => ['', '', `${query.data.station.toUpperCase()} minutes of ${prettyDate(new Date(timestamp*1000))}`, 
					'', '', `[${query.data.filtered.reduce((s, a) => s + (a == null ? 0 : 1), 0)}/60]`],
			},
			{
				size: 40,
				gap: 0,
				values: (u, vals) => vals.map(v => v.toFixed(0)),
				font: font(12),
				stroke: color('text'),
				grid: { show: true, stroke: color('grid'), width: 2 },
			}
		],
		series: [
			{ stroke: color('text') },
			{
				width: 2,
				stroke: color('green'),
				points: { fill: color('bg'), stroke: color('green') }
			},
			{
				width: 1,
				stroke: color('cyan'),
				points: { show: true, fill: color('bg'), stroke: color('cyan') }
			},
			{
				width: 1,
				stroke: color('magenta'),
				points: { size: 8, show: true, fill: color('magenta'), stroke: color('magenta') }
			}
		],
		hooks: {
			ready: [
				(u: uPlot) => u.setCursor({ left: -1, top: -1 }) // ??
			]
		}
	} as uPlot.Options;
	
	return (
		<div style={{ position: 'absolute' }}>
			<UplotReact {...{ options, data: [
				Array.from(Array(60).keys()),
				Array(60).fill(query.data.integrated),
				query.data.filtered,
				query.data.raw.map((v, i) => v === query.data.filtered[i] ? null : v)
			] }}/>
		</div>);
}
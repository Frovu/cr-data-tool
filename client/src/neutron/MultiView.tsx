import { useQuery } from 'react-query';
import uPlot from 'uplot';
import { color, customTimeSplits, font } from '../plotUtil';
import UplotReact from 'uplot-react';
import { useState } from 'react';
import { useSize } from '../util';

function plotOptions(stations: string[]) {
	return {
		tzDate: ts => uPlot.tzDate(new Date(ts * 1e3), 'UTC'),
		legend: { show: false },
		padding: [10, 12, 6, 0],
		axes: [
			{
				font: font(14),
				stroke: color('text'),
				grid: { show: true, stroke: color('grid'), width: 2 },
				ticks: { stroke: color('grid'), width: 2 },
				// ...customTimeSplits()
			},
			{
				font: font(14),
				stroke: color('text'),
				labelSize: 20,
				labelGap: 0,
				size: 46,
				gap: 2,
				grid: { show: true, stroke: color('grid'), width: 2 },
				ticks: { stroke: color('grid'), width: 2 },
			}
		],
		series: [
			{ value: '{YYYY}-{MM}-{DD} {HH}:{mm}', stroke: color('text') }
		].concat(stations.map(s => ({
			label: s.toUpperCase(),
			stroke: color('cyan'),
			grid: { stroke: color('grid'), width: 1 },
			points: { fill: color('bg'), stroke: color('cyan') },

		} as any)))
	} as Omit<uPlot.Options, 'height'|'width'>;
}

function queryFunction(path: string, interval: [Date, Date], stations: string[]) {
	return async () => {
		const urlPara = new URLSearchParams({
			from: (interval[0].getTime() / 1000).toFixed(0),
			to:   (interval[1].getTime() / 1000).toFixed(0),
			stations: stations.join(),
		}).toString();
		const res = await fetch(process.env.REACT_APP_API + path + '?' + urlPara);
		if (res.status !== 200)
			throw Error('HTTP '+res.status);
		const body = await res.json() as { rows: any[][], fields: string[] };
		if (!body?.rows.length) return null;
		const ordered = body.fields.map((_, i) => body.rows.map(row => row[i]));
		console.log(path, '=>', body);
		return { data: ordered, fields: body.fields };
	};
}

export function ManyStationsView({ interval }: { interval: [Date, Date] }) {
	const stations = ['all'];
	const query = useQuery(['manyStations', stations, interval], queryFunction('api/neutron', interval, stations));

	const [container, setContainer] = useState<HTMLDivElement | null>(null);
	const size = useSize(container?.parentElement);

	if (query.isLoading)
		return <div className='center'>LOADING...</div>;
	if (query.isError)
		return <div className='center' style={{ color: color('red') }}>FAILED TO LOAD</div>;
	if (!query.data)
		return <div className='center'>NO DATA</div>;
	
	const { data, fields } = query.data;
	const options = { ...size, ...plotOptions(fields.slice(1)) };

	return (<div ref={node => setContainer(node)} style={{ position: 'absolute' }}>
		<UplotReact {...{ options, data: data as any }}/>
	</div>);
}
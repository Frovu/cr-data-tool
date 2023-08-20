import { useMutation, useQuery, useQueryClient } from 'react-query';
import { useMonthInput } from '../neutron/Neutron';
import { apiGet } from '../util';
import uPlot from 'uplot';
import { NavigatedPlot, NavigationContext, color, font, useNavigationState, axisDefaults, seriesDefaults } from '../plotUtil';
import { useMemo, useRef } from 'react';

const spacecraft: any = {
	51: 'WIND',
	52: 'WIND',
	71: 'ACE',
	60: 'GeoT'
};

function plotOptions(): Omit<uPlot.Options, 'height'|'width'> {
	return {
		padding: [12, 12, 0, 8],
		axes: [
			{
				...axisDefaults(),
				font: font(14),
			}, {
				...axisDefaults(),
				scale: 'imf',
				size: 36,
				font: font(12),
			}, {
				...axisDefaults(),
				scale: 'V',
				size: 36,
				side: 1,
				grid: {},
				font: font(12),
			}
		],
		scales: {
			V: {
				range:  (u, min, max) => [1.2*min - max, max+20]
			},
			imf: {
				range:  (u, min, max) => [min - max, max*2]
			},
			T: {
				distr: 3
			},
			Dst: {
				range:  (u, min, max) => [min, max + (max-min)*2]
			}
		},
		series: [
			{ value: '{YYYY}-{MM}-{DD} {HH}:{mm}', stroke: color('text') },
			{
				...seriesDefaults('🛰sw', 'white'),
				value: (u, val) => val ? (spacecraft[val] ?? val?.toString()) : '--',
				show: false
			}, {
				...seriesDefaults('🛰imf', 'white'),
				value: (u, val) => val ? (spacecraft[val] ?? val?.toString()) : '--',
				show: false
			}, {
				...seriesDefaults('T', 'skyblue'),
				value: (u, val) => val?.toFixed(0) ?? '--',
				show: false
			}, {
				...seriesDefaults('D', 'peach'),
				show: false
			}, {
				...seriesDefaults('V', 'acid')
			}, {
				...seriesDefaults('Tidx', 'blue'),
				value: (u, val) => val?.toFixed(2) ?? '--',
				show: false
			}, {
				...seriesDefaults('β', 'magenta'),
				show: false
			}, {
				...seriesDefaults('|B|', 'purple', 'imf')
			}, {
				...seriesDefaults('Bx', 'cyan', 'imf'),
				show: false
			}, {
				...seriesDefaults('By', 'green', 'imf'),
				show: false
			}, {
				...seriesDefaults('Bz', 'red', 'imf'),
				show: false
			}, {
				...seriesDefaults('Dst', 'green')
			}, {
				...seriesDefaults('Kp', 'crimson'),
				show: false
			}, {
				...seriesDefaults('Ap', 'crimson'),
				show: false
			}
		],
		hooks: {
			ready: [
				(u) => {
					const values = Array.from(u.root.children[1].children).map(tr => tr.children[1]) as HTMLTableCellElement[];
					values.forEach(td => {
						td.parentElement!.style.marginRight = '8px';
						(td.parentElement!.firstChild as HTMLElement).style.padding = '0';
						td.style.padding = '4px';
					});
					values[0].style.width = '17ch';
					values[1].style.width = '5ch';
					values[2].style.width = '5ch';
					values[3].style.width = '6ch';
					values.slice(4).forEach(td => { td.style.width = '5ch'; });
				}
			]
		}
	};
}

export function Omni() {
	const [interval, monthInput] = useMonthInput(new Date(Date.now() - 864e5 * 60));
	const legendContainer = useRef<HTMLDivElement>(null);

	const query = useQuery<{ fields: string[], rows: number[][] }>(['omni', interval], () => apiGet('omni', {
		from: Math.floor(interval[0].getTime() / 1e3),
		to:   Math.floor(interval[1].getTime() / 1e3),
		query: 'spacecraft_id_sw,spacecraft_id_imf,sw_temperature,sw_density,sw_speed,temperature_idx,plasma_beta,imf_scalar,imf_x,imf_y,imf_z,dst_index,kp_index,ap_index'
	}));

	const navigation = useNavigationState();
	const data = useMemo(() => {
		return query.data?.fields.map((f, i) => query.data.rows.map(r => r[i]));
	}, [query.data]);

	console.log(JSON.stringify(navigation.state));

	return (<div style={{ display: 'grid', height: 'calc(100% - 6px)', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
		<NavigationContext.Provider value={navigation}>
			<div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
				<div style={{ textAlign: 'center', marginRight: 16 }}>
					[ {monthInput} ]
				</div>
				<div ref={legendContainer}>

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
					return <NavigatedPlot {...{ data: data!, options: plotOptions, legendHeight: 72 }}/>;
				})()}
			</div>
		</NavigationContext.Provider>
	</div>);
}
import { useMutation, useQuery, useQueryClient } from 'react-query';
import { useMonthInput } from '../neutron/Neutron';
import { apiGet, apiPost, prettyDate, useEventListener } from '../util';
import uPlot from 'uplot';
import { NavigatedPlot, NavigationContext, color, font, useNavigationState, axisDefaults, seriesDefaults } from '../plotUtil';
import { useEffect, useMemo, useState } from 'react';

const PARAM_GROUP = ['all', 'SW', 'IMF', 'Geomag'] as const;
const spacecraft: any = {
	45: 'IMP8',
	50: 'IMP8',
	51: 'Wind',
	52: 'WinD',
	71: 'ACE',
	81: 'DSCVR',
	60: 'GeoT'
};

function plotOptions(): Omit<uPlot.Options, 'height'|'width'> {
	const filterV =  (u: uPlot, splits: number[]) => splits.map(sp => sp > 200 ? sp : null);
	const filterB = (u: uPlot, splits: number[]) => [ null, null, ...splits.slice(2, -2), null, null, null ];
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
				filter: filterB,
				ticks: { stroke: color('grid'), width: 2, filter: filterB },
				font: font(12),
			}, {
				...axisDefaults(),
				scale: 'V',
				size: 36,
				ticks: { stroke: color('grid'), width: 2, filter: filterV },
				filter: filterV,
				grid: {},
				side: 1,
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
				...seriesDefaults('🛰imf', 'white', '🛰sw'),
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
				...seriesDefaults('V', 'acid'),
				value: (u, val) => val?.toFixed(0) ?? '--',
			}, {
				...seriesDefaults('Tidx', 'blue'),
				value: (u, val) => val?.toFixed(2) ?? '--',
				show: false
			}, {
				...seriesDefaults('β', 'magenta'),
				show: false
			}, {
				...seriesDefaults('|B|', 'purple', 'imf'),
				width: 2
			}, {
				...seriesDefaults('Bx', 'cyan', 'imf'),
				show: false
			}, {
				...seriesDefaults('By', 'green', 'imf'),
				show: false
			}, {
				...seriesDefaults('Bz', 'crimson', 'imf'),
			}, {
				...seriesDefaults('Dst', 'green')
			}, {
				...seriesDefaults('Kp', 'cyan'),
				show: false
			}, {
				...seriesDefaults('Ap', 'cyan'),
				show: false
			}
		],
		hooks: {
			ready: [
				(u) => {
					if (!u.root.children[1]) return;
					const values = Array.from(u.root.children[1].children).map(tr => tr.children[1]) as HTMLTableCellElement[];
					values.forEach(td => {
						td.parentElement!.style.marginRight = '8px';
						(td.parentElement!.firstChild as HTMLElement).style.padding = '0';
						td.style.padding = '4px';
					});
					values[0].style.width = '17ch';
					values[1].style.width = '5ch';
					values[2].style.width = '5ch';
					values[3].style.width = '7ch';
					values.slice(4).forEach(td => { td.style.width = '5ch'; });
				}
			]
		}
	};
}

export function Omni() {
	const queryClient = useQueryClient();
	const [interval, monthInput] = useMonthInput(new Date(Date.now() - 864e5 * 60));
	const [group, setGroup] = useState<typeof PARAM_GROUP[number]>('all');
	const [overwrite, setOverwrite] = useState(false);
	const [report, setReport] = useState<{ error?: string, success?: string }>({});
	const navigation = useNavigationState();

	const query = useQuery<{ fields: string[], rows: number[][] }>(['omni', interval], () => apiGet('omni', {
		from: interval[0],
		to:   interval[1],
		query: 'spacecraft_id_sw,spacecraft_id_imf,sw_temperature,sw_density,sw_speed,temperature_idx,plasma_beta,imf_scalar,imf_x,imf_y,imf_z,dst_index,kp_index,ap_index'
	}));

	const data = useMemo(() => {
		if (query.data?.rows.length! <= 1)
			return null;
		const plotData = query.data?.fields.map((f, i) => query.data.rows.map(r => r[i]));
		console.log('data:', plotData);
		return plotData;
	}, [query.data]);

	const { min, max } = (navigation.state.selection ?? navigation.state.view);
	const [fetchFrom, fetchTo] = !data ? interval : [min, max].map(i => data[0][i]);

	const mutation = useMutation(async (sat: string) => {
		const rm = sat === 'remove';
		const { cursor, selection } = navigation.state;
		if (rm && (!data || (!cursor?.lock && !selection)))
			return '';
		const [from, to] = !rm ? [fetchFrom, fetchTo] :
			cursor?.lock ? Array(2).fill(data![0][cursor.idx]) :
				[selection!.min, selection!.max].map(i => data![0][i]);

		const res = await apiPost(rm ? 'omni/remove' : 'omni/fetch', {
			from, to,
			group,
			...(!rm && { 
				source: sat,
				overwrite 
			})
		});
		return res.message;
	}, {
		onSuccess: (success: string) => {
			queryClient.invalidateQueries('omni');
			setReport({ success });
		},
		onError: (e: Error) => {
			setReport({ error: e.toString() });
		}
	});

	useEventListener('keydown', (e: KeyboardEvent) => {
		if (e.code === 'Delete')
			mutation.mutate('remove');
		if (e.shiftKey && e.code === 'KeyO')
			mutation.mutate('omniweb');
		if (e.shiftKey && e.code === 'KeyA')
			mutation.mutate('ace');
		if (e.shiftKey && e.code === 'KeyD')
			mutation.mutate('dscovr');
	});

	useEffect(() => {
		const what = navigation.state.chosen?.label;
		if (what)
			setGroup(['V','T','Tidx','D'].includes(what) ? 'SW' : ['|B|','Bx','By','Bz'].includes(what) ? 'IMF' : 'all');
	}, [navigation.state.chosen]);

	return (<div style={{ display: 'grid', height: 'calc(100% - 6px)', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
		<NavigationContext.Provider value={navigation}>
			<div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
				<div style={{ textAlign: 'center', marginRight: 16 }}>
					[ {monthInput} ]
				</div>
				<div style={{ padding: '8px 16px', lineHeight: '2em' }}>
					<div onWheel={(e) => setGroup(g => PARAM_GROUP[(PARAM_GROUP.indexOf(g) + (e.deltaY > 0 ? 1 : -1) + PARAM_GROUP.length) % PARAM_GROUP.length])}>
						Parameter group: <select style={{ color: color({ all: 'cyan', SW: 'acid', IMF: 'purple', Geomag: 'peach' }[group]) }}
							value={group} onChange={(e) => setGroup(e.target.value as any)}>
							{PARAM_GROUP.map(pa => <option key={pa} value={pa}>{pa}</option>)}
						</select>
					</div>
					<div onWheel={(e) => setOverwrite(ow => !ow)}>
						<label> Overwrite present data:
							<input type='checkbox' checked={overwrite} onChange={e => setOverwrite(e.target.checked)} hidden={true}/>
							<span style={{ color: color(overwrite ? 'magenta' : 'cyan') }}> {overwrite ? 'true' : 'false'}</span>
						</label></div>
					{fetchTo && fetchFrom && <>
						<div style={{ color: color('cyan'), margin: 4, verticalAlign: 'top' }}>
							[{Math.ceil((fetchTo - fetchFrom) / 3600)} h]
							<div style={{ display: 'inline-block', color: color('text-dark'), textAlign: 'right', lineHeight: 1.25 }}>
								{prettyDate(new Date(1e3 * fetchFrom))}<br/>
								&nbsp;&nbsp;to {prettyDate(new Date(1e3 * fetchTo))}
							</div>
						</div>
						<div style={{ margin: '4px 0 8px 16px', lineHeight: '36px' }}>
							<button style={{ width: 196 }} onClick={() => mutation.mutate('omniweb')}>Fetch OMNI&nbsp;&nbsp;</button>
							<button style={{ width: 196 }} onClick={() => mutation.mutate('ace')}>Fetch ACE&nbsp;&nbsp;&nbsp;</button>
							<button style={{ width: 196 }} onClick={() => mutation.mutate('dscovr')}>&nbsp;Fetch DSCOVR&nbsp;</button>
							<button style={{ width: 196 }} onClick={() => mutation.mutate('geomag')}>&nbsp;Fetch Geomag&nbsp;</button>
							<button style={{ width: 196 }} onClick={() => mutation.mutate('remove')}>&nbsp;REMOVE POINTS</button>
						</div>
					</>}
					<div style={{ margin: '16px 0 0 4px', lineHeight: 1.5, cursor: 'pointer' }} onClick={() => setReport({})}>
						<div style={{ color: color('red') }}>{report.error}</div>
						<div style={{ color: color('green') }}>{report.success}</div>
					</div>
				</div>
			</div>
			<div style={{ position: 'relative', height: 'min(100%, calc(100vw / 2))', border: '2px var(--color-border) solid' }}>
				{(()=>{
					if (query.isLoading)
						return <div className='center'>LOADING...</div>;
					if (query.isError)
						return <div className='center' style={{ color: 'var(--color-red)' }}>FAILED TO LOAD</div>;
					if (!data)
						return <div className='center'>NO DATA</div>;
					return <NavigatedPlot {...{ data: data!, options: plotOptions, legendHeight: 72 }}/>;
				})()}
			</div>
		</NavigationContext.Provider>
	</div>);
}
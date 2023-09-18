import { useMemo, useState } from 'react';
import { apiGet, apiPost, prettyDate, useMonthInput } from '../util';
import { NavigatedPlot, NavigationContext, useNavigationState, axisDefaults, seriesDefaults, color } from '../plotUtil';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import uPlot from 'uplot';

const ORDER = ['time', 'original', 'revised', 'corrected', 'predicted', 't_mass_average', 'pressure'];

function options(): Omit<uPlot.Options, 'width'|'height'> {
	const filter = (dir: number): uPlot.Axis.Filter => (u, splits, ax) => {
		const scale = u.scales[u.axes[ax].scale!];
		const threshold = scale.min! + (scale.max! - scale.min!) * 2 / 3;
		return splits.map((spl, i) => (dir > 0 ? spl > threshold : spl < threshold) ? spl : null);
	};
	return {
		padding: [12, 0, 0, 0],
		scales: {
			temp: {
				range: (u, min, max) => [min-(max-min)*2, max+1]
			},
			press: {
				range: (u, min, max) => [min-(max-min)*2, max+1]
			},
			variation: {
				range: (u, min, max) => [min-.1, max+(max-min)*2/3]
			}
		},
		axes: [
			{
				
				...axisDefaults(),
			}, {
				...axisDefaults(true, filter(-1)),
				scale: 'variation',
				values: (u, vals) => vals.map(v => v == null ? '' : v.toString() + ' %')
			}, {
				...axisDefaults(false, filter(1)),
				scale: 'temp',
				ticks: { show: false },
				gap: -36,
				size: 12,
				values: (u, vals) => vals.map(v => v == null ? '' : v.toString() + ' K')
			}, {
				...axisDefaults(false, filter(1)),
				side: 1,
				scale: 'press',
				values: (u, vals) => vals.map(v => v?.toString())
			}
		],
		series: [
			{
				label: 't',
				value: '{YYYY}-{MM}-{DD} {HH}:{mm}',
				stroke: color('text')
			}, {
				...seriesDefaults('original', 'purple', 'variation'),
				value: (u, val) => val?.toFixed(2) ?? '--',
				points: { show: true, size: 2, fill: color('purple') },
				width: 2,
			}, {
				...seriesDefaults('revori', 'blue', 'variation'),
				value: (u, val) => val?.toFixed(2) ?? '--',
			}, {
				...seriesDefaults('corrected', 'green', 'variation'),
				value: (u, val) => val?.toFixed(2) ?? '--'
			}, {
				...seriesDefaults('predicted', 'orange', 'variation'),
				value: (u, val) => val?.toFixed(2) ?? '--',
			}, {
				...seriesDefaults('t_m', 'gold', 'temp'),
				value: (u, val) => val?.toFixed(2) ?? '--'
			}, {
				...seriesDefaults('p', 'purple', 'press'),
				value: (u, val) => val?.toFixed(1) ?? '--'
			}
		]
	};
}

export default function MuonApp() {
	const queryClient = useQueryClient();
	const [interval, monthInput] = useMonthInput(new Date(Date.now() - 864e5*365), 12);
	const [experiment, setExperiment] = useState('Moscow-pioneer');
	const [averaging, setAveraging] = useState(1);
	const navigation = useNavigationState();

	const query = useQuery({
		queryKey: ['muon', interval],
		queryFn: () => apiGet<{ fields: string[], rows: (number | null)[][] }>('muon', {
			from: interval[0],
			to: interval[1],
			experiment,
			query: 'original,revised,corrected,t_mass_average,pressure'
		})
	});
	const gsmQuery = useQuery(['muon/predicted'], () => apiGet<{ fields: string[], rows: (number | null)[][] }>('muon/predicted', {
		from: interval[0],
		to: interval[1],
		experiment,
	}));

	const plotData = useMemo(() => {
		if (!query.data || query.data.rows.length < 2) return null;

		const length = query.data.rows.length;
		const gsmData = gsmQuery.data?.rows;
		const data = Object.fromEntries(query.data.fields.map((f, i) => [f, query.data.rows.map(row => row[i])]));
		const indexGsm = data['time'].findIndex(t => gsmData?.[0]?.[0] === t); // NOTE: presumes that gsm result has no gaps
		data['predicted'] = Array(length).fill(null);
		if (gsmData && indexGsm >= 0) {
			for (let i = 0; i < gsmData.length && indexGsm + i < length; ++i) {
				data['predicted'][indexGsm + i] = gsmData[i][1];
			}
		}
		
		const variationSeries = ['revised', 'corrected', 'predicted'];
		const varAverages = variationSeries.map(ii =>
			data[ii].reduce((a, b) => a! + (b ?? 0), 0)! / data[ii].filter(v => v != null).length);
		data['original'] = data['original'].map((v, i) => v !== data['revised'][i] ? v : null);
		for (const [i, ser] of variationSeries.entries())
			data[ser] = data[ser].map(v => v == null ? null : (v - varAverages[i]) / (1 + varAverages[i] / 100));
		
		const series = ORDER.map(s => data[s]);
		if (averaging === 1)
			return series;

		const averaged = series.map(s => Array(Math.ceil(length / averaging) + 1).fill(null));
		for (let ai = 0; ai < averaged[0].length; ++ai) {
			const cur = ai * averaging;
			averaged[0][ai] = series[0][cur];
			for (let si = 1; si < series.length; ++si) {
				let acc = 0, cnt = 0;
				for (let i = 0; i < averaging; ++i) {
					const val = series[si][cur + i];
					if (val == null)
						continue;
					acc += val;
					++cnt;
				}
				averaged[si][ai] = cnt === 0 ? null : acc / cnt;
			}
		}
		averaged[0][averaged[0].length - 1] = data['time'][length-1]; // a hack to prevent plot reset due to bound times change

		return averaged;
	}, [query.data, gsmQuery.data, averaging]);

	const { min, max } = (navigation.state.selection ?? navigation.state.view);
	const [fetchFrom, fetchTo] = (!plotData || (min === 0 && max === plotData[0].length - 1))
		? interval : [min, max].map(i => plotData[0][i]!);

	type mutResp = { status: 'busy'|'ok'|'error', downloading?: { [key: string]: number }, message?: string };
	const obtainMutation = useMutation(() => apiPost<mutResp>('muon/obtain', {
		from: fetchFrom,
		to: fetchTo,
		experiment
	}), {
		onSuccess: ({ status }) => {
			if (status === 'busy') {
				setTimeout(() => obtainMutation.mutate(), 500);
			} else {
				if (status === 'ok')
					queryClient.invalidateQueries('muon');
				setTimeout(() => obtainMutation.isSuccess && obtainMutation.reset(), 3000);
			}
		}
	});
	
	const computeMutation = useMutation(() => apiPost('muon/compute', {
		from: fetchFrom,
		to: fetchTo,
		experiment
	}), {
		onSuccess: () => queryClient.invalidateQueries('muon')
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
					<div style={{ padding: 16 }}>
						<label>Average over <input style={{ width: 48, textAlign: 'center' }}
							type='number' min='1' max='24' value={averaging} onChange={e => setAveraging(e.target.valueAsNumber)}/> h</label>

					</div>
					<div style={{ paddingBottom: 8 }}>
						<button style={{ padding: 2, width: 196 }} disabled={isObtaining} onClick={() => obtainMutation.mutate()}>
							{isObtaining ? 'stand by...' : 'Obtain everything'}</button>
						{obtainMutation.data?.status === 'ok' && <span style={{ paddingLeft: 8, color: color('green') }}>OK</span>}
					</div>
					<button style={{ padding: 2, width: 196 }} disabled={computeMutation.isLoading}
						onClick={() => computeMutation.mutate()}>{computeMutation.isLoading ? '...' : 'Compute corrected'}</button>
					<div style={{ paddingTop: 4 }}>
						<div>{(obtainMutation.data?.status === 'busy' && obtainMutation.data?.message)}</div>
						{Object.entries(obtainMutation.data?.downloading ?? {}).map(([year, progr]) => <div key={year}>
							downloading {year}: <span style={{ color: color('acid') }}>{(progr * 100).toFixed(0)} %</span>
						</div>)}
						<div style={{ color: color('red') }}>{obtainMutation.error?.toString() ??
							(obtainMutation.data?.status === 'error' && obtainMutation.data?.message)}
						{computeMutation.error?.toString()}</div>
					</div>
				</div>
			</div>
			<div style={{ position: 'relative' }}>
				{query.isLoading && <div className='center'>LOADING...</div>}
				{query.data && !plotData && <div className='center'>NO DATA</div>}
				{plotData && <NavigatedPlot {...{ data: plotData, options, legendHeight: 72 }}/>}
			</div>
		</div>
	</NavigationContext.Provider>;
}
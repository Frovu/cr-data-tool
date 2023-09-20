import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost, prettyDate, useMonthInput } from '../util';
import { NavigatedPlot, NavigationContext, useNavigationState, axisDefaults, seriesDefaults, color, ScatterPlot } from '../plotUtil';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import regression from 'regression';
import uPlot from 'uplot';

const ORDER = ['time', 'original', 'revised', 'corrected', 'expected', 't_mass_average', 'pressure'];

type ChannelDesc = {
	name: string,
	correction: {
		coef_t: number,
		coef_p: number,
		coef_v: number,
		time: number,
		length: number,
		modified: boolean
	} | null
};
type MuonContextType = {
	experiments: {
		name: string,
		since: number,
		until: number | null,
		channels: ChannelDesc[]
	}[]
};
const MuonContext = createContext<MuonContextType>({} as any);

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
				...seriesDefaults('original', 'magenta', 'variation'),
				value: (u, val) => val?.toFixed(2) ?? '--',
				points: { show: true, width: .1, size: 4, fill: color('magenta') },
				width: 1,
			}, {
				...seriesDefaults('revori', 'blue', 'variation'),
				value: (u, val) => val?.toFixed(2) ?? '--',
			}, {
				...seriesDefaults('corrected', 'green', 'variation'),
				value: (u, val) => val?.toFixed(2) ?? '--'
			}, {
				...seriesDefaults('expected', 'orange', 'variation'),
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

function MuonApp() {
	const queryClient = useQueryClient();
	const { experiments } = useContext(MuonContext);
	const experimentNames = experiments.map(exp => exp.name);
	const [interval, monthInput] = useMonthInput(new Date(Date.now() - 864e5*365), 12, 48);
	const [{ experiment, channel }, setExperiment] = useState(() => ({ experiment: experimentNames[0], channel: 'V' }));
	const { channels, until, since } = experiments.find(exp => exp.name === experiment)!;
	const corrInfo = channels.find(c => c.name === channel)?.correction;
	const [averaging, setAveraging] = useState(1);
	const navigation = useNavigationState();

	const query = useQuery({
		queryKey: ['muon', interval, experiment, channel],
		queryFn: () => apiGet<{ fields: string[], rows: (number | null)[][] }>('muon', {
			from: interval[0],
			to: interval[1],
			experiment,
			query: 'original,revised,corrected,expected,t_mass_average,pressure'
		})
	});

	const [plotData, nonnull] = useMemo(() => {
		if (!query.data || query.data.rows.length < 2) return [null, null];

		const length = query.data.rows.length;
		const data = Object.fromEntries(query.data.fields.map((f, i) => [f, query.data.rows.map(row => row[i])]));
		
		const variationSeries = ['revised', 'corrected', 'expected'];
		const varAverages = variationSeries.map(ii =>
			data[ii].reduce((a, b) => a! + (b ?? 0), 0)! / data[ii].filter(v => v != null).length);
		data['original'] = data['original'].map((v, i) => v !== data['revised'][i] ? v : null);
		for (const [i, ser] of [...variationSeries.entries()].concat([[0, 'original']]))
			data[ser] = data[ser].map(v => v == null ? null : (v - varAverages[i]) / (1 + varAverages[i] / 100));

		const counts = Object.fromEntries(Object.entries(data)
			.map(([ser, vals]) => [ser, vals.filter(v => v != null).length]));
		
		const series = ORDER.map(s => data[s]);
		if (averaging === 1)
			return [series, counts];

		const averaged: (number | null)[][] = series.map(s => Array(Math.ceil(length / averaging) + 1).fill(null));
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

		return [averaged, counts];
	}, [query.data, averaging]);

	const { min, max } = (navigation.state.selection ?? navigation.state.view);
	const [fetchFrom, fetchTo] = (!plotData || (min === 0 && max === plotData[0].length - 1))
		? interval : [min, max].map(i => plotData[0][i]!) as [number, number]; // can this be null??

	const queryParams = { from: fetchFrom, to: fetchTo, experiment, channel };
	const queryCoef = useQuery(['muon', 'coef', interval, experiment, channel],
		() => apiGet<{ coef_t: number, coef_p: number, coef_v: number, length: number }>('muon/compute', { 
			...queryParams,
			from: since,
			to: until ?? Math.floor(Date.now()/1e3)
		}));
	const queryCoefLocal = useQuery(['muon', 'coef', fetchFrom, fetchTo, experiment, channel],
		() => {
			if (fetchTo - fetchFrom < 86400 * 10)
				return null;
			return apiGet<{ coef_t: number, coef_p: number, coef_v: number, length: number }>('muon/compute',
				{ ...queryParams, from: fetchFrom, to: fetchTo });
		});

	const correlationPlot = useMemo(() => {
		if (!plotData) return null;
		const [xColIdx, yColIdx] = ['corrected', 'expected'].map(f => ORDER.indexOf(f));
		const data = plotData;
		const filtered: [number, number][] = [...data[0].keys()].filter(i => fetchFrom <= data[0][i]! && data[0][i]! <= fetchTo
			&& data[xColIdx][i] != null && data[yColIdx][i] != null).map(i => [data[xColIdx][i]!, data[yColIdx][i]!]);
		if (filtered.length < 2) return null;
		const transposed = [0, 1].map(i => filtered.map(r => r[i])) as [number[], number[]];
		
		const minX = Math.min.apply(null, transposed[0]);
		const maxX = Math.max.apply(null, transposed[0]);
		const regr = regression.linear(filtered, { precision: 8 });
		const regrX = Array(128).fill(0).map((_, i) => minX + i * (maxX - minX) / 128);
		const regrY = regrX.map(x => regr.predict(x)[1]);

		return <>
			<div style={{ paddingBottom: 4 }}>
				pred(corr): a={regr.equation[0].toFixed(2)}, R<sup>2</sup>={regr.r2.toFixed(2)}
			</div>
			<div style={{ position: 'relative', height: 280 }}>
				<ScatterPlot data={[transposed, [regrX, regrY]]} colour='orange'/>
			</div>
		</>;
	}, [plotData, fetchFrom, fetchTo]);

	type mutResp = { status: 'busy'|'ok'|'error', downloading?: { [key: string]: number }, message?: string };
	const obtainMutation = useMutation(() => apiPost<mutResp>('muon/obtain', queryParams), {
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

	const revisionMut = useMutation((action: 'remove'|'revert') => apiPost('muon/revision', {
		from: navigation.state.cursor?.lock ? plotData![0][navigation.state.cursor.idx] : fetchFrom,
		to: navigation.state.cursor?.lock ? plotData![0][navigation.state.cursor.idx] : fetchTo,
		experiment,
		channel,
		action
	}), {
		onSuccess: () => queryClient.invalidateQueries('muon')
	});

	type MutCoef = { coef_p?: number, coef_t?: number, length?: number, modified?: boolean };
	const coefMut = useMutation(({ coef_p, coef_t, length, modified }: MutCoef) => apiPost('muon/coefs', { // eslint-disable-line camelcase
		experiment, channel, coef_p, coef_t, length, modified // eslint-disable-line camelcase
	}), {
		onSuccess: () => queryClient.invalidateQueries('muon')
	});

	const defaultInput = () => Object.fromEntries((['coef_p', 'coef_t'] as const).map(coef =>
		[coef, corrInfo ? (corrInfo[coef]*100).toFixed(3) : '?']));
	const [input, setInputState] = useState(defaultInput);
	useEffect(() => setInputState(defaultInput()), [corrInfo]); // eslint-disable-line

	const coefs = [queryCoef, queryCoefLocal].map(q => q.data &&
		['coef_p', 'coef_t', 'coef_v'].map((c) => (q.data![c as keyof typeof q.data] * 100).toFixed(c === 'coef_v' ? 2 : 3)));
	const rmCount = plotData && (navigation.state.cursor?.lock ? 1 : (fetchTo - fetchFrom) / 3600);
	const isObtaining = obtainMutation.isLoading || (obtainMutation.isSuccess && obtainMutation.data.status === 'busy');
	return <NavigationContext.Provider value={navigation}>
		<div style={{ height: '100%', display: 'grid', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
			<div style={{ overflowY: 'scroll' }}>
				<div>
					<label>Experiment: <select value={experiment} style={{ maxWidth: 150 }}
						onChange={e => setExperiment(exp => ({ experiment: e.target.value, channel: 'V' }))}>
						{experimentNames.map(exp => <option key={exp} value={exp}>{exp}</option>)}
					</select></label>
					<label title='Telescope channel'>:<select value={channel} style={{ width: 42, textAlign: 'center' }}
						onChange={e => setExperiment(exp => ({ ...exp, channel: e.target.value }))}>
						{channels.map(({ name }) => <option key={name} value={name}>{name}</option>)}
					</select></label>
				</div>
				<div style={{ color: color('text-dark'), fontSize: 14, textAlign: 'right', paddingRight: 14 }}>
					operational { until ? 'from' : 'since'} {prettyDate(since, true)} { until ? 'to ' + prettyDate(until, true) : '' }
				</div>
				<div style={{ paddingTop: 4 }}>
					Show: {monthInput}
				</div>
				{plotData && <div style={{ paddingTop: 8 }}>
					<label>Average over <input style={{ width: 42, textAlign: 'center' }}
						type='number' min='1' max='24' value={averaging} onChange={e => setAveraging(e.target.valueAsNumber)}/> h</label>
				</div>}
				{nonnull && <div style={{ paddingTop: 8, paddingRight: 8, display: 'flex', justifyContent: 'space-between' }}>
					<span style={{ color: color('border') }}>[<span title='Total points'>{nonnull['time']}</span>
						{nonnull['original'] > 0 && <span title='Revised points' style={{ color: color('magenta') }}>-{nonnull['original']}</span>}
					]</span>
					<span title='Revised coverage' style={{ color: color('cyan') }}>[{(nonnull['revised']/nonnull['time']*100).toFixed(1)}%]</span>
					<span title='Corrected coverage' style={{ color: color('green') }}>[{(nonnull['corrected']/nonnull['time']*100).toFixed(1)}%]</span>
					<span title='Temperature coverage' style={{ color: color('gold') }}>[{(nonnull['t_mass_average']/nonnull['time']*100).toFixed(0)}%]</span>
					<span title='GSM expected coverage' style={{ color: color('orange') }}>[{(nonnull['expected']/nonnull['time']*100).toFixed(0)}%]</span>
				</div>}
				{plotData && <table style={{ textAlign: 'center' }}>
					<tr>
						<td></td><td>_p</td><td>_t</td><td style={{ color: color('text-dark') }}>_v</td>
					</tr>
					<tr title='Computed using all available data'>
						<td>&nbsp;all:</td>{coefs[0] && <><td>{coefs[0][0]}</td><td>{coefs[0][1]}</td><td style={{ color: color('text-dark') }}>{coefs[0][2]}</td>
							<td><button style={{ marginLeft: 4, padding: '0 12px' }}
								onClick={()=>coefMut.mutate({ ...queryCoef.data! })}>use</button></td></>}
					</tr>
					<tr title='Computed using data from viewed/selected interval'>
						<td>&nbsp;cur:</td>{coefs[1] && <><td>{coefs[1][0]}</td><td>{coefs[1][1]}</td><td style={{ color: color('text-dark') }}>{coefs[1][2]}</td>
							<td><button style={{ marginLeft: 4, padding: '0 12px' }}
								onClick={()=>coefMut.mutate({ ...queryCoefLocal.data! })}>use</button></td></>}
					</tr>
					<tr title='Actually used for corrections (saved)'>
						<td>used:</td>
						{(['coef_p', 'coef_t'] as const).map((coef, i) => <td>
							<input type='text' style={{ width: 56, textAlign: 'center', color: color(corrInfo ? 'text' : 'red') }}
								value={input[coef]}
								onChange={e => setInputState(st => ({ ...st, [coef]: e.target.value }))}
								onKeyDown={e => ['Escape', 'Enter'].includes(e.code) && (e.target as HTMLInputElement)?.blur()}
								onBlur={e => !isNaN(parseFloat(e.target.value)) &&
									coefMut.mutate({ ...corrInfo, [coef]: parseFloat(e.target.value)/100, modified: true })}/>
						</td>)}
					</tr>
				</table>}
				{plotData && <div style={{ paddingLeft: 8, fontSize: 14, color: color('text-dark') }}>
					{corrInfo == null && <>coefficients are not set</>}
					{corrInfo && <>
						set per {corrInfo.length && `[${Math.floor(corrInfo.length / 24)} d] `}
						at {prettyDate(corrInfo.time)}
						{corrInfo.modified && <div>(modified manually)</div>}
					</>}
				</div>}
				<div style={{ paddingTop: 4 }}>
					{correlationPlot}
				</div>
				<div style={{ paddingTop: 8 }}>
					<div style={{ color: color('text'), verticalAlign: 'top' }}>
							[{Math.ceil((fetchTo - fetchFrom) / 3600) + 1} h]
						<div style={{ display: 'inline-block', color: color('text-dark'), textAlign: 'right', lineHeight: 1.25 }}>
							{prettyDate(fetchFrom)}<br/>
							&nbsp;&nbsp;to {prettyDate(fetchTo)}
						</div>
					</div>
					<div style={{ paddingTop: 8 }} title='Re-obatin all data for focused interval'>
						<button style={{ padding: 2, width: 196 }} disabled={isObtaining} onClick={() => obtainMutation.mutate()}>
							{isObtaining ? 'stand by...' : 'Obtain everything'}</button>
						{obtainMutation.data?.status === 'ok' && <span style={{ paddingLeft: 8, color: color('green') }}>OK</span>}
					</div>
					{plotData && <div style={{ paddingTop: 8 }} title='Mask selected points (this is kind of reversible)'>
						<button style={{ padding: 2, width: 196 }} disabled={revisionMut.isLoading}
							onClick={() => revisionMut.mutate('remove')}>{revisionMut.isLoading ? '...' : `Remove ${rmCount} point${rmCount === 1 ? '' : 's'}`}</button>
					</div>}
					{plotData && <div style={{ paddingTop: 8 }} title='Clear all revisions (this action is irreversible)'>
						<button style={{ padding: 2, width: 196, borderColor: color('red') }} disabled={revisionMut.isLoading}
							onClick={() => revisionMut.mutate('revert')}>{revisionMut.isLoading ? '...' : 'Clear revisions'}</button>
					</div>}
				</div>
				<div style={{ paddingTop: 8 }}>
					<div>{(obtainMutation.data?.status === 'busy' && obtainMutation.data?.message)}</div>
					{Object.entries(obtainMutation.data?.downloading ?? {}).map(([year, progr]) => <div key={year}>
						downloading {year}: <span style={{ color: color('acid') }}>{(progr * 100).toFixed(0)} %</span>
					</div>)}
					<div style={{ color: color('red'), cursor: 'pointer' }} onClick={() => {
						revisionMut.reset();
						obtainMutation.reset();
						coefMut.reset();
					}}>
						{query.error?.toString()}
						{coefMut.error?.toString()}
						{revisionMut.error?.toString()}
						{obtainMutation.error?.toString()}
						{obtainMutation.data?.status === 'error' && obtainMutation.data?.message}
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

export default function MuonWrapper() {
	const query = useQuery(['muon', 'experiments'], () =>
		apiGet<MuonContextType>('muon/experiments'));

	const parsed = useMemo((): MuonContextType | null => {
		if (!query.data) return null;
		console.log('muon experiments: ', query.data.experiments);
		return query.data;
	}, [query.data]);

	return <>
		{query.isLoading && <div>Loading experiments list...</div>}
		{query.isError && <div style={{ color: color('red') }}>Failed to load experiments: {query.error?.toString()}</div>}
		{parsed && parsed.experiments.length < 1 && <div>No experiments found</div>}
		{parsed && parsed.experiments.length > 0 && <MuonContext.Provider value={parsed}>
			<MuonApp/>
		</MuonContext.Provider>}
	</>;
}
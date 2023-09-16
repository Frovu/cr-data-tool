import { useQuery } from 'react-query';
import { NavigationContext, useNavigationState } from '../plotUtil';
import { apiGet, useMonthInput } from '../util';

export default function TemperatureApp() {
	const [interval, monthInput] = useMonthInput(new Date(Date.now() - 864e5 * 30));
	const navigation = useNavigationState();

	const query = useQuery({
		queryKey: ['temperature', interval],
		queryFn: () => apiGet<{ status: 'ok' | 'busy', downloading?: { [key: string]: number } }>('temperature', {
			from: interval[0],
			to: interval[1],
			lat: 55.47,
			lon: 37.32,
		}),
		refetchInterval: (data) => data?.status === 'busy' ? 500 : false
	});

	return <NavigationContext.Provider value={navigation}>
		<div style={{ height: '100%', display: 'grid', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
			<div>
				{monthInput}
				{query.data?.status}
				{Object.entries(query.data?.downloading ?? {}).map(([year, progr]) => <div>
					downloading {year}: {(progr * 100).toFixed(1)} %
				</div>)}
			</div>
			<div>
			</div>

		</div>
	</NavigationContext.Provider>;
}
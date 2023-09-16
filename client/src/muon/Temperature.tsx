import { NavigationContext, useNavigationState } from '../plotUtil';
import { useMonthInput } from '../util';

export default function TemperatureApp() {
	const [interval, monthInput] = useMonthInput(new Date(Date.now() - 864e5 * 30));
	const navigation = useNavigationState();

	return <NavigationContext.Provider value={navigation}>
		<div style={{ height: '100%', display: 'grid', gridTemplateColumns: '360px 1fr', gap: 4, userSelect: 'none' }}>
			<div>
				{monthInput}
			</div>
			<div>

			</div>

		</div>
	</NavigationContext.Provider>;
}
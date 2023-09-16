import { useState } from 'react';
import { useMonthInput } from '../util';

export default function MuonApp() {
	const [interval, monthInput] = useMonthInput();

	return <div>
		{monthInput}
	</div>;
}
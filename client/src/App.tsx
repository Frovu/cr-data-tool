import { QueryClient, QueryClientProvider, useMutation, useQuery } from 'react-query';
import Neutron from './neutron/Neutron';
import { useEffect, useState } from 'react';
import { apiGet, apiPost, useEventListener } from './util';
import { Omni } from './omni/Omni';
import MuonApp from './muon/Muon';
import TemperatureApp from './muon/Temperature';
import { color } from './plotUtil';

const theQueryClient = new QueryClient();

function AuthPrompt() {
	const [error, setError] = useState('');
	const [login, setLogin] = useState('');
	const [password, setPassword] = useState('');

	const mutation = useMutation(() => apiPost('auth', { login, password }), {
		onError: (e: any) => setError(e.toString()),
		onSuccess: () => theQueryClient.invalidateQueries('auth')
	});

	useEventListener('keydown', (e: KeyboardEvent) => {
		e.stopImmediatePropagation();
	});

	return (<>
		<div className='popupBackground'></div>
		<div className='popup' style={{ left: '50%', top: '40%', textAlign: 'right', padding: '1em 3em' }} autoFocus onKeyDown={e => e.nativeEvent.stopImmediatePropagation()}>
			<h3>AUTHORIZATION REQUIRED</h3>
			<p>
				LOGIN: <input type='text' style={{ width: '11em', borderColor: 'var(--color-border)', textAlign: 'center' }}
					value={login} onChange={e => setLogin(e.target.value)}/>
			</p><p>
				PASSWORD: <input type='password' style={{ width: '11em', borderColor: 'var(--color-border)', textAlign: 'center' }}
					value={password} onChange={e => setPassword(e.target.value)}/>
			</p>
			<p><button style={{ padding: '1px 2em' }} onClick={() => mutation.mutate()}>LOG IN</button></p>
			<div style={{ height: '1em', color: 'var(--color-red)' }}>{error}</div>
		</div>
	</>);
}

function App() {
	const query = useQuery(['auth'], () => apiGet<{ login: string | null }>('auth'));
	const app = ['temperature', 'muon', 'neutron', 'omni'].find(a => window.location.pathname.endsWith(a)) ?? 'crdt';
	useEffect(() => {
		document.title = {
			temperature: 'CRDT: temperature',
			neutron: 'CRDT: NM',
			muon: 'CRDT: Muon',
			omni: 'CRDT: Omni',
			crdt: 'CRDT'
		}[app]!;
	}, [app]);
	
	return (
		<div className='bbox' style={{ height: '100vh', width: '100vw', padding: 8 }}>
			{query.isError && <div style={{ color: color('red'), position: 'fixed', left: 16, bottom: 16 }}>FAILED TO LOAD AUTH</div>}
			{!['crdt', 'temperature'].includes(app) && query.data && query.data.login == null && <AuthPrompt/>}
			{app === 'temperature' && <TemperatureApp/>}
			{app === 'neutron' && <Neutron/>}
			{app === 'muon' && <MuonApp/>}
			{app === 'omni' && <Omni/>}
			{app === 'crdt' && <div style={{ margin: '2em 3em', lineHeight: '2em', fontSize: 20 }}>
				<h4>Select an application:</h4>
				- <a href='temperature'>Atmospheric temperature</a><br/>
				- <a href='neutron'>Neutron monitors</a><br/>
				- <a href='muon'>Muon telescopes</a><br/>
				- <a href='omni'>Interplanetary medium (omni)</a>
			</div>}
		</div>
	);
}

export default function AppWrapper() {
	return (
		<QueryClientProvider client={theQueryClient}>
			<App/>
		</QueryClientProvider>
	);
}
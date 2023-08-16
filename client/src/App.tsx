import { QueryClient, QueryClientProvider, useMutation, useQuery } from 'react-query';
import Neutron from './neutron/Neutron';
import { useState } from 'react';
import { useEventListener } from './util';

const theQueryClient = new QueryClient();

function AuthPrompt() {
	const [error, setError] = useState('');
	const [login, setLogin] = useState('');
	const [password, setPassword] = useState('');

	const mutation = useMutation(async () => {
		const res = await fetch(`${process.env.REACT_APP_API}api/auth`, {
			method: 'POST', credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ login, password })
		});
		if (res.status === 400)
			throw new Error('Bad request');
		if (res.status === 404)
			throw new Error('User not found');
		if (res.status === 401)
			throw new Error('Wrong password');
		if (res.status !== 200)
			throw new Error(`HTTP: ${res.status}`);
		return await res.text();
	}, {
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
	const query = useQuery(['auth'], async () => {
		const res = await fetch(`${process.env.REACT_APP_API}api/auth`, { credentials: 'include' });
		if (res.status !== 200)
			throw new Error('HTTP '+res.status);
		return await res.json() as { login: string | null };
	});
	
	return (
		<div className='bbox' style={{ height: '100vh', width: '100vw', padding: 8 }}>
			{query.isError && <div className='center'>FAILED TO LOAD</div>}
			{query.data && query.data.login == null && <AuthPrompt/>}
			<Neutron/>
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
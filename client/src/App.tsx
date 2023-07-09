import { QueryClient, QueryClientProvider } from 'react-query';
import Neutron from './neutron/Neutron';

const theQueryClient = new QueryClient();

function App() {
	return (
		<div className='bbox' style={{ height: '100vh', width: '100vw', padding: 4 }}>
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
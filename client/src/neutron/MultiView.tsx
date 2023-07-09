import { useQuery } from 'react-query';

function queryFunction(path: string, interval: [Date, Date], stations: string[]) {
	return async () => {
		const urlPara = new URLSearchParams({
			from: (interval[0].getTime() / 1000).toFixed(0),
			to:   (interval[1].getTime() / 1000).toFixed(0),
			stations: stations.join(),
		}).toString();
		const res = await fetch(process.env.REACT_APP_API + path + '?' + urlPara);
		if (res.status !== 200)
			throw Error('HTTP '+res.status);
		const body = await res.json() as { data: any[][], fields: string[] };
		if (!body?.data.length) return null;
		const ordered = body.fields.map((_, i) => body.data.map(row => row[i]));
		console.log(path, '=>', ordered, body.fields);
		return [ordered, body.fields];
	};
}

export function ManyStationsView({ interval }: { interval: [Date, Date] }) {
	const stations = ['all'];
	const query = useQuery(['manyStations', stations, interval], queryFunction('api/neutron', interval, stations));

	return <>Hellow</>
}
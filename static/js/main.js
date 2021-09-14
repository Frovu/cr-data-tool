import * as applications from './applications.js';
import initPlot from './plot.js';

async function plot() {
	const resp = await applications.query('temperature');
	console.log(resp);
	let plotData = [Array(resp.data.length) // resp.fields.map(()=>Array(resp.data.length));
		, Array(resp.data.length), Array(resp.data.length), Array(resp.data.length)];
	for (let i = 0; i < resp.data.length; ++i) {
		const row = resp.data[i];
		plotData[0][i] = row[0];
		plotData[1][i] = row[1];
		plotData[2][i] = row[2];
		plotData[3][i] = row[3];
		// for (let j = 1; j < row.length; ++j) {
		// 	plotData[j][i] = row[j];
		// }
	}
	initPlot(plotData);
}

plot();
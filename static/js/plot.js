import uPlot from './uPlot.iife.min.js';

const MIN_HEIGHT = 360;
let uplot;
const parentEl = document.getElementsByClassName('graph')[0];

function getPlotSize() {
	const height = parentEl.offsetWidth * 0.5;
	return {
		width: parentEl.offsetWidth,
		height: height > MIN_HEIGHT ? height : MIN_HEIGHT,
	};
}

export default function initPlot(data) {
	uplot = new uPlot({
		...getPlotSize(),
		series: [
			{
				value: '{YYYY}-{MM}-{DD} {HH}:{mm}'
			},
			{
				stroke: 'red',
				label: 'Temperature',
				scale: 'K',
				value: (u, v) => v == null ? '-' : v.toFixed(1) + ' K',
			},
			{
				stroke: 'green',
				label: 'Temperature',
				scale: 'K',
				value: (u, v) => v == null ? '-' : v.toFixed(1) + ' K',
			},
			{
				stroke: 'blue',
				label: 'Temperature',
				scale: 'K',
				value: (u, v) => v == null ? '-' : v.toFixed(1) + ' K',
			}
		],
		axes: [
			{},
			{
				scale: 'K',
				values: (u, vals) => vals.map(v => v.toFixed(0) + ' K'),
			},
		],
		cursor: {
			drag: { dist: 16 },
			points: { size: 6, fill: (self, i) => self.series[i]._stroke }
		}
	}, data, parentEl);
	window.addEventListener('resize', () => {
		uplot.setSize(getPlotSize());
	});
}

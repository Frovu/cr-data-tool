import * as plot from '../plot.js';
import * as tabs from '../tabsUtil.js';
import * as temp from './temperature.js';

const LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30, 20, 10];
const params = {
	date: Math.floor(Date.now()/1000) - 86400*10,
	lat: 55.47,
	lon: 37.32
};
let temperatureUnit = 'K';
let data;

function receiveData(resp) {
	const row = resp.data[0];
	data = [];
	LEVELS.forEach(field => {
		data.push(row[resp.fields.indexOf(field)]);
	});
	plot.data(data);
}

function plotInit() {
	const transform = temperatureUnit!=='K' && (t => t-273.15);
	plot.init([
		{ scale: 'height' },
		{ scale: temperatureUnit, transform }
	]);
	plot.series([
		{
			scale: 'height',

		}, {
			scale: temperatureUnit,
			label: 'Temperature',
			color: 'rgba(0,255,255,0.8)',
			precision: 1,
			transform
		}
	]);
	plot.data(data);
}

export function initTabs() {
	tabs.fill('app', [
		tabs.text(`<h4>Description</h4>
Application retrieves atmospheric temperature data of <a href="https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html">NCEP/NCAR Reanalysis project</a> and interpolates it for given coordinates and shows vertical temperature gradient curve.
<h4>Usage</h4>
The button on "Query" tab indicates your data query progress.
When query parameters are changed, the button becomes highlighted.`)
	]);
	temp.fetchStations().then(ss => {
		tabs.fill('query', [
			!ss ? tabs.text('Stations failed to load, please refresh tab') :
				tabs.input('station', (lat, lon) => {
					params.lat = lat;
					params.lon = lon;
					temp.settingsChanged();
				}, { text: 'in', list: ss, lat: params.lat, lon: params.lon }),
			tabs.input('time', (from, to, force) => {
				params.from = Math.floor(from.getTime() / 1000);
				params.to = Math.floor(to.getTime() / 1000);
				if (force)
					temp.fetchData(params, receiveData);
				else
					temp.settingsChanged();
			}, { from: new Date(params.from*1000), to: new Date(params.to*1000) }),
			temp.queryBtn
		]);
	});
	tabs.fill('view', [
		tabs.input('switch', unit => {
			temperatureUnit = unit;
			plotInit();
		}, { options: ['K', '°C'], text: 'Unit: ' })
	]);
	tabs.disable('tools');
	tabs.disable('export');
}

export function load() {
	plotInit();
	temp.fetchData();
}

export function unload() {
	temp.stopFetch();
}

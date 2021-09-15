import * as temperature from './applications/temperature.js';

export const applications = {
	temperature
};

let active;

export async function swith(app) {
	active = app;
}

export async function query(app) {
	return applications[app].fetchData();
}

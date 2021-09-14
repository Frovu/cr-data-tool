import * as temperature from './applications/temperature.js';

const applications = {
	temperature
};

// let active = 'temperature';

export async function query(app) {
	return applications[app].fetchData();
}

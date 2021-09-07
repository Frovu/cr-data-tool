import * as temperature from './applications/temperature.js';

const applications = {
	temperature
};

export function ping() {
	for (const m in applications) {
		applications[m].ping();
	}
}

import * as applications from './applications.js';

setInterval(function () {
	applications.ping();
}, 500);

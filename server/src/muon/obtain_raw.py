from datetime import datetime
import logging
import requests, json

log = logging.getLogger('crdt')

def _obtain_moscow(t_from: int, t_to: int, experiment: str, what: str):
	dev = 'muon-pioneer' if experiment == 'Moscow-pioneer' else None
	what = what if what == 'pressure' else 'vertical'
	assert dev is not None
	query = f'https://tools.izmiran.ru/sentinel/api/data?from={t_from}&to={t_to+3600}&dev={dev}&fields={what}'
	res = requests.get(query, timeout=10000)
	if res.status_code != 200:
		logging.warning(f'Muones: failed raw -{res.status_code}- {experiment} {t_from}:{t_to}')
		return []
	json_data = json.loads(res.text)
	data = json_data['rows']
	result = [(datetime.utcfromtimestamp(line[0]), line[1]) for line in data]
	logging.debug(f'Muones: got raw [{len(result)}/{(t_to-t_from)//60+1}] {experiment}:{what} {t_from}:{t_to}')
	return result

def _obtain_apatity(t_from, t_to, experiment, what='source'):
	url = 'https://cosmicray.pgia.ru/json/db_query_mysql.php'
	dbn = 'full_muons' if experiment == 'Apatity' else 'full_muons_barentz'
	res = requests.get(f'{url}?db={dbn}&start={t_from}&stop={t_to}&interval=60', timeout=5000)
	if res.status_code != 200:
		logging.warning(f'Muones: failed raw -{res.status_code}- {experiment} {t_from}:{t_to}')
		return []
	target = 'pressure_mu' if what == 'pressure' else 'mu_dn'
	data = json.loads(res.text)
	result = [(datetime.utcfromtimestamp(line['timestamp']), line[target]) for line in data]
	logging.debug(f'Muones: got raw [{len(result)}/{(t_to-t_from)//60+1}] {experiment} {t_from}:{t_to}')
	return result

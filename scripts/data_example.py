from datetime import datetime, timezone
import requests, json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

url = 'https://crst.izmiran.ru/crdt'

def obtain_data(station: str, dt_from: datetime, dt_to: datetime, channel: str='V'):
    tfr, tto = [int(d.replace(tzinfo=timezone.utc).timestamp()) for d in (dt_from, dt_to)]
    para = f'from={tfr}&to={tto}&station={station}&channel={channel}&coefs=saved'
    uri = f'{url}/api/muones?{para}'
    while True:
        res = requests.get(uri, verify=False)
        if res.status_code != 200:
            print(f'request failed: {res.status_code}')
            return None, None
        body = json.loads(res.text)
        status = body['status']
        assert status != 'failed'
        if status != 'ok':
            print(f'{dt_from}: {status} {body.get("info") or ""}')
            time.sleep(1)
        else:
            return body.get('data'), body.get('fields') # body['info'] should contain coefficients

if __name__ == '__main__':
    dt_from = datetime(2021, 1, 5)
    dt_to = datetime(2022, 1, 5)
    data, fields = obtain_data('Apatity', dt_from, dt_to)

    # convert timestamp to datetime
    import numpy as np
    data = np.array(data, dtype='object')
    data[:,0] = [datetime.utcfromtimestamp(d) for d in data[:,0]]

    # "pretty" print
    print("   ".join(['    date']+fields))
    for l in data[:7]:
        print("\t".join([str(i) for i in l]))
    print('...')
    for l in data[-7:]:
        print("\t".join([str(i) for i in l]))

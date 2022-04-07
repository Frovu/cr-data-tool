import concurrent.futures
import requests
import gzip
import re
import os

URL = 'http://cosray.shinshu-u.ac.jp/crest/DB/Public/Archives'
PATH = 'tmp/gmdn'

def dump_one(type, year_url, gz=False, retry=1):
    try:
        year = re.search(r'([0-9]{4})', year_url).group()
        station = re.search(r'([A-Za-z]+)', year_url).group().replace('FPGA', '')
        directory = f'{PATH}/{station}_{type}'
        if not os.path.exists(directory):
            os.makedirs(directory)
        fp = f'{directory}/{year}.txt{".gz" if gz else ""}'
        if os.path.isfile(fp):
            print(f'found local {station}/{year}')
            return
        print(f'downloading {station}/{year}')
        res = requests.get(f'{URL}/{type}/{year_url}', stream=True)
        if res.status_code == 200:
            with gzip.open(fp, 'wb') if gz else open(fp, 'wb') as file:
                for chunk in res.iter_content(chunk_size=None):
                    file.write(chunk)
                return print(f'done {station}/{year}')
        else:
            print(f'failed {station}/{year} {res.status_code}')
    except Exception as e:
        print(f'error {station}/{year}: {e}')
    if retry > 0: dump_one(type, year_url, gz, retry-1)

def dump(type):
    page = requests.get(f'{URL}/{type}.php')
    year_re = re.compile(rf'<a href=["\']{type}/([a-zA-Z0-9/\.]+)["\']')
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for year_url in year_re.findall(page.text):
            executor.submit(dump_one, type, year_url)

dump('GMDN')
dump('UGMD')

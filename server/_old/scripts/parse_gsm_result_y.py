from datetime import datetime
import os, psycopg2, psycopg2.extras
pg_conn = psycopg2.connect(
    dbname = os.environ.get("MUON_DB_NAME") or "cr_cr",
    user = os.environ.get("MUON_DB_USER") or "crdt",
    password = os.environ.get("MUON_DB_PASS"),
    host = os.environ.get("MUON_DB_HOST") )

PATH = 'tmp/GSM.txt'

def parse():
    print(f'Reading file: {PATH}')
    with open(PATH) as file:
        for line in file:
            if '-'*64 in line:
                break
        data = []
        for line in file:
            split = line.split()
            time = datetime.strptime(split[0]+'T'+split[1], '%Y-%m-%dT%H:%M:%S+00')
            data.append((time, *[float(v) for v in split[2:]]))
    print(f'Parsed [{len(data)}] from {data[0][0]} to {data[-1][0]}')
    print('Inserting...', end='')
    with pg_conn.cursor() as cursor:
        query = 'INSERT INTO gsm_result VALUES %s ON CONFLICT(time) DO NOTHING'
        psycopg2.extras.execute_values(cursor, query, data)
        pg_conn.commit()
    print('done!')

if __name__ == '__main__':
    parse()

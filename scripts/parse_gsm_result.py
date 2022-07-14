from datetime import datetime
import os, psycopg2, psycopg2.extras
pg_conn = psycopg2.connect(
    dbname = os.environ.get("MUON_DB_NAME") or "cr_cr",
    user = os.environ.get("MUON_DB_USER") or "crdt",
    password = os.environ.get("MUON_DB_PASS"),
    host = os.environ.get("MUON_DB_HOST") )

PATH = 'tmp/GSM.dat'

def parse():
    print(f'Reading file: {PATH}')
    with open(PATH) as file:
        for line in file:
            if '-'*64 in line:
                break
        data = []
        for line_number, line in enumerate(file, 1):
            if line == '\n': continue
            try:
                split = line.split()
                time = datetime(*[int(d) for d in split[0].split('.')], int(split[1])-1)
                data.append((time, *[float(v) for v in split[3:]]))
            except Exception as e:
                print(f'Failed on line header+{line_number}:')
                print([line])
                print(e)
                return
    print(f'Parsed [{len(data)}] from {data[0][0]} to {data[-1][0]}')
    print('Inserting...', end='')
    with pg_conn.cursor() as cursor:
        query = 'INSERT INTO gsm_result VALUES %s ON CONFLICT(time) DO NOTHING'
        psycopg2.extras.execute_values(cursor, query, data)
        pg_conn.commit()
    print('done!')

if __name__ == '__main__':
    parse()

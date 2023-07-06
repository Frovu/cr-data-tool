from datetime import datetime
import os, psycopg2, psycopg2.extras
pg_conn = psycopg2.connect(
    dbname = os.environ.get("MUON_DB_NAME") or "cr_cr",
    user = os.environ.get("MUON_DB_USER") or "crdt",
    password = os.environ.get("MUON_DB_PASS"),
    host = os.environ.get("MUON_DB_HOST") )

SRC = 'tmp/MCRL'

if __name__ == '__main__':
    pressure, cube = [], []
    for fname in sorted(os.listdir(SRC)):
        with open(f'{SRC}/{fname}') as file:
            lines = file.readlines()
        lasttime = 0
        for line in lines[2:]:
            sp = line.split()
            time = datetime.strptime(sp[0]+'T'+sp[1], '%Y-%m-%dT%H:%M:%S+00')
            if time == lasttime:
                print('skip double line', time)
                continue
            lasttime = time
            pressure.append([time, float(sp[26])])
            cube.append([time, float(sp[32])])
        print(f'[{len(cube)}] < {fname}')
    print('inserting')
    with pg_conn.cursor() as cursor:
        q = '''INSERT INTO muon_counts_60m (time, source, channel)
        SELECT time, source, (SELECT id FROM muon_channels WHERE station_name = \'Moscow-CUBE\')
        FROM (VALUES %s) s(time, source) ON CONFLICT (time, channel) DO UPDATE SET source = EXCLUDED.source'''
        psycopg2.extras.execute_values(cursor, q, cube)
        q = '''INSERT INTO muon_conditions_60m (time, pressure, station)
        SELECT time, pressure, (SELECT id FROM muon_stations WHERE name = \'Moscow-CUBE\')
        FROM (VALUES %s) s(time, pressure) ON CONFLICT (time, station) DO UPDATE SET pressure = EXCLUDED.pressure'''
        psycopg2.extras.execute_values(cursor, q, pressure)
        pg_conn.commit()
    print('done')

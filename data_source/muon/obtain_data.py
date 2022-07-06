from datetime import datetime, timedelta
from core.sql_queries import integrity_query
import psycopg2, logging, os
import requests, json
from subprocess import Popen, PIPE, check_output

def _psql_query(table, period, t_from, t_to, fields, epoch=False, count=False, cond=''):
    interval = f'interval \'{period} seconds\''
    return f'''WITH periods AS
(SELECT generate_series(to_timestamp({t_from}), to_timestamp({t_to}), {interval}) period)
SELECT {'EXTRACT(EPOCH FROM period)::integer' if epoch else 'period'} AS time,{'COUNT(*),'if count else ''}{', '.join([f'ROUND(AVG({f})::numeric, 3)::real as {f}' for f in fields[1:]])}
FROM periods LEFT JOIN {table} ON (period <= {fields[0]} AND {fields[0]} < period + {interval} {cond})
GROUP BY period ORDER BY period
'''

def _obtain_local(station, dt_from, dt_to, what):
    year, month = dt_from.year, dt_from.month
    dir = f'tmp/{station}'
    result = []
    is_weird = station == 'Yakutsk' and what == 'pressure'
    while year < dt_to.year or (year == dt_to.year and month <= dt_to.month):
        fpath = f'{dir}/{what}/{year%100:02}{month:02}.txt'
        if is_weird: fpath = f'{dir}/pressure.txt'
        if os.path.exists(fpath):
            with open(fpath) as file:
                for line in file:
                    date, time, value = line.split()
                    time = datetime.strptime(date+'T'+time, '%Y-%m-%dT%H:%M:%S+00') # meh
                    result.append((time, float(value)/10 if is_weird else float(value)))
        if is_weird: break
        month += 1
        if month > 12:
            month = 1
            year += 1
    return result

def _obtain_gmdn(station, dt_from, dt_to, what):
    # FIXME: some station will not have Pres. column
    is_channel = what != 'pressure'
    col_name = what if is_channel else 'Pres.'
    dir = next(d for d in os.listdir('tmp/gmdn') if station in d)
    result = []
    for year in range(dt_from.year, dt_to.year + 1):
        fpath = f'tmp/gmdn/{dir}/{year}.txt'
        if not os.path.exists(fpath):
            continue
        with open(fpath) as file:
            for line in file:
                if '*'*32 in line:
                    columns = last.split()
                    break
                last = line
            idx = columns.index(col_name)
            for line in file:
                split = line.split()
                time = datetime(*[int(i) for i in split[:4]])
                val = (float(split[idx]) / 60) if is_channel else float(split[idx]) # /60 for ppm
                result.append([time, val])
    return result

# doesn't support non-hour resolutions
def _obtain_yakutsk(station, dt_from, dt_to, what):
    target = 'p' if what == 'pressure' else what.lower() + '_ur'
    level = station.split('_')[-1]
    url = f'''https://www.ysn.ru/ipm/yktMT{level}/?station=yktk60_{level}&res1=1hour
&year1={dt_from.year}&mon1={dt_from.month}&day1={dt_from.day}&hour1={dt_from.hour}
&year2={dt_to.year}&mon2={dt_to.month}&day2={dt_to.day}&hour2={dt_to.hour}
&interval_type=from_to&separator=Space&ors=UNIX&oformlenie=stub&field={target}&output=ASCIIFile'''
    res = requests.get(url, stream=True)
    if res.status_code != 200:
        logging.warning(f'Muones: failed raw -{res.status_code}- {station}:{what} {dt_from}:')
        return []
    result = []
    for line in res.iter_lines():
        date, time, value = line.split()
        tstamp = datetime.strptime(date+'T'+time, '%Y-%m-%dT%H:%M:%S+00') # FIXME: use separator=bar instead
        result.append((tstamp, float(value)))
    return result

def _obtain_apatity(station, t_from, t_to, channel='V', what='source', period=3600):
    url = 'https://cosmicray.pgia.ru/json/db_query_mysql.php'
    dbn = 'full_muons' if station == 'Apatity' else 'full_muons_barentz'
    res = requests.get(f'{url}?db={dbn}&start={t_from}&stop={t_to}&interval={period//60}')
    if res.status_code != 200:
        logging.warning(f'Muones: failed raw -{res.status_code}- {station}:{channel} {t_from}:{t_to}')
        return []
    target = 'pressure_mu' if what == 'pressure' else 'mu_dn'
    data = json.loads(res.text)
    if not data:
        trim = datetime.now().timestamp() // period * period - period
        stop = int(trim) if t_to > trim else t_to
        return [(datetime.utcfromtimestamp(t), -1) for t in range(t_from, stop+1, period)]
    result = []
    for line in data:
        time = datetime.utcfromtimestamp(int(line['timestamp']) // period * period)
        result.append([time, line[target]])
    logging.debug(f'Muones: got raw [{len(result)}/{(t_to-t_from)//period+1}] {station}:{channel} {t_from}:{t_to}')
    return result

def _obtain_gdrive(station, dt_from, dt_to, channel='V', what='source'):
    result = []
    for year in range(dt_from.year, dt_to.year + 1):
        try:
            list = check_output(['gdrive', 'list', '-q', f'title contains \'{station}.{year}\' and mimeType != \'application/vnd.google-apps.folder\''], text=True)
            list = list.splitlines()
            if len(list) < 2:
                logging.debug(f'gdrive: not found {station}.{year}')
                continue
            id, title = list[1].split()[:2]
            logging.debug(f'gdrive: downloading {title} ({id})')
            gdrive = Popen(['gdrive', 'download', '-s', '-i', id], stdout=PIPE, text=True)
            for line in gdrive.stdout:
                if '*'*64 in line:
                    break
            columns = gdrive.stdout.readline().lower().split()
            target = channel if what == 'source' else what
            if not target.lower() in columns:
                logging.warning(f'gdrive: no such column ({target}) {title}')
                continue
            target_idx = columns.index(target.lower())
            if 'timestamp' in columns:
                t_idx = columns.index('timestamp')
                get_time = lambda sp: datetime.utcfromtimestamp(sp[t_idx])
            elif 'datetime' in columns:
                templ, t_idx = '%Y-%m-%dT%H:%M:%S', columns.index('timestamp')
                get_time = lambda sp: datetime.strptime(sp[t_idx].slice(0, len(templ)), templ)
            elif 'date' in columns and 'time' in columns:
                d_idx, t_idx = columns.index('date'), columns.index('time')
                get_time = lambda sp: datetime.strptime(date+'T'+time, '%Y-%m-%dT%H:%M:%S')
            elif 'dt' in columns:
                base, t_idx = datetime(year, 1, 1), columns.index('dt')
                get_time = lambda sp: base + timedelta(days=float(sp[t_idx]))
            else:
                logging.warning(f'gdrive: time not found {title}')
                continue
            if what == 'source':
                unit = title.split('.')[2]
                if unit == '60m':
                    divisor = 60
                elif unit == '05m':
                    divisor = 60
                elif unit == '01m':
                    divisor = 1
                elif unit == 'hz':
                    divisor = 1 / 60
                else:
                    logging.warning(f'gdrive: unknown unit {title}')
                    continue
            else:
                divisor = 1
            for line in gdrive.stdout:
                split = line.split()
                result.append((get_time(split), float(split[target_idx]) / divisor))
        except Exception as e:
            logging.warning(f'gdrive: failed {station}.{year} - {e}')
    return result

def obtain(channel, t_from, t_to, column):
    station = channel.station_name
    what = column if column == 'pressure' else channel.name
    logging.debug(f'Muones: querying {what} {station}:{channel.name} {t_from}:{t_to}')
    if station == 'Moscow-pioneer':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            with conn.cursor() as cursor:
                col = 'n_v' if column == 'source' else column
                cursor.execute(_psql_query('muon_data', channel.period, t_from, t_to, ['dt', col]))
                resp = cursor.fetchall()
                return resp, column
    elif station in ['Apatity', 'Barentsburg']:
        data = _obtain_apatity(station, t_from, t_to, channel.name, column)
        return data, column

    dt_from, dt_to = [datetime.utcfromtimestamp(t) for t in [t_from, t_to]]
    if 'Yakutsk_' in station:
        return _obtain_yakutsk(station, dt_from, dt_to, what), column
    if station == 'Yakutsk':
        return _obtain_local(station, dt_from, dt_to, what), column
    if station == 'Nagoya':
        result = _obtain_gmdn(station, dt_from, dt_to, what)
        if not result:
            return _obtain_local(station, dt_from, dt_to, what), column
        if result[0][0] > dt_from:
            result = _obtain_local(station, dt_from, result[0][0]-timedelta(hours=1), what) + result
        if result[-1][0] < dt_to:
            result = result + _obtain_local(station, result[-1][0]+timedelta(hours=1), dt_to, what)
        return result, column
    if station == 'Moscow-CARPET':
        data = _obtain_gdrive(station.split('-')[1], dt_from, dt_to, channel.name, column)
        return data, column

    logging.error(f'Unknown muon station {station}')
    return [], column

def obtain_raw(station, t_from, t_to, period, fields=None):
    if station == 'Moscow-pioneer':
        with psycopg2.connect(dbname = os.environ.get('MUON_MSK_DB'),
            user = os.environ.get('MUON_MSK_USER'),
            password = os.environ.get('MUON_MSK_PASS'),
            host = os.environ.get('MUON_MSK_HOST')) as conn:
            fl = ['dt', 'c0', 'c1', 'n_v', 'pressure', 'temperature', 'temperature_ext', 'voltage']
            with conn.cursor() as cursor:
                q = _psql_query('muon_data', period, t_from, t_to, [fl[0]] + fields if fields else fl, epoch=True, count=False)
                cursor.execute(q)
                return cursor.fetchall(), [desc[0] for desc in cursor.description]

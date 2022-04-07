
def integrity_query(t_from, t_to, period, tables, test_columns, time_column='time',
    bad_condition=False, bad_cond_columns=[], join_overwrite=False, where='', return_epoch=True):
    if type(test_columns) is not list:
        test_columns = [test_columns]
    if not join_overwrite and type(tables) is not list:
        tables = [tables]
    not_null_cond = ' AND '.join([f'{c} IS NOT NULL' for c in test_columns])
    null_cond = ' OR '.join([f'{c} IS NULL' for c in test_columns])
    join_tables = join_overwrite or '\n\t'.join([f'LEFT JOIN {t} ON (ser.tm = {t}.{time_column})' for t in tables])
    return f'''WITH RECURSIVE
input (t_from, t_to, t_interval) AS (
    VALUES (to_timestamp({t_from}), to_timestamp({t_to}), interval \'{period} s\')
), filled AS (
    SELECT
        ser.tm as time, {','.join(test_columns + bad_cond_columns)}
    FROM
        (SELECT generate_series(t_from, t_to, t_interval) tm FROM input) ser
        {join_tables}
    ORDER BY time
), rec AS (
    SELECT
        t_from AS gap_start, t_from-t_interval AS gap_end
    FROM input
    UNION
    SELECT
        gap_start,
        COALESCE((SELECT time-t_interval FROM filled
            WHERE ({f"NOT ({bad_condition}) AND" if bad_condition else ""} {not_null_cond})
                AND time > gap_start LIMIT 1),t_to) AS gap_end
    FROM (
        SELECT
            (SELECT time FROM filled WHERE ({f"({bad_condition}) OR" if bad_condition else ""} {null_cond})
                AND time > gap_end LIMIT 1) AS gap_start
        FROM rec, input
        WHERE gap_end < t_to
    ) r, input )
SELECT {", ".join([f"EXTRACT(EPOCH FROM {f})::integer" if return_epoch else f for f in ["gap_start", "gap_end"]])}
FROM rec WHERE gap_end - gap_start >= interval \'{period} s\' OR (gap_end = gap_start AND EXTRACT(EPOCH FROM gap_end)::integer%{period}=0);'''

def aggregate_periods(t_from, t_to, period, table, select, time_column='time', condition=''):
    interval = f'interval \'{period}\''
    t_to = f'to_timestamp({t_to})' if t_to else 'CURRENT_TIMESTAMP+' + interval
    return f'''WITH periods AS
    (SELECT generate_series(to_timestamp({t_from}), {t_to}, {interval}) period)
    SELECT EXTRACT(EPOCH FROM period)::integer AS time,
        {select}
    FROM (periods LEFT JOIN {table} ON (period <= {time_column} AND {time_column} < period + {interval})) as agg
    {condition and ('WHERE ' + condition)}
    GROUP BY period ORDER BY period'''

def remove_spikes(table, channel, threshold=0.02):
    return f'''WITH data(time, cur, next, prev) AS (
    SELECT
        time, source,
        LEAD(source) OVER (ORDER BY time) AS next,
        LAG(source) OVER (ORDER BY time) AS prev
    FROM {table} WHERE channel = {channel})
    UPDATE data SET source = -1, corrected = NULL
        WHERE cur > 0 AND ((prev < 0 AND next < 0)
        OR (prev < 0 AND next > 0 AND ABS(cur / next - 1) > {threshold})
        OR (next < 0 AND prev > 0 AND ABS(cur / prev - 1) > {threshold})
        OR (prev > 0 AND next > 0 AND ABS(next/ prev - 1) < {threshold} AND ABS(cur / next - 1) > {threshold}))'''

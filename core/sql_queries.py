
def integrity_query(t_from, t_to, period, table, test_column, time_column='time', return_epoch=True):
    return f'''WITH RECURSIVE
input (t_from, t_to, t_interval) AS (
    VALUES (to_timestamp({t_from}), to_timestamp({t_to}), interval \'{period} seconds\')
), filled AS (
    SELECT
        ser.tm as time, {test_column}
    FROM
        (SELECT generate_series(t_from, t_to, t_interval) tm FROM input) ser
    LEFT JOIN {table}
        ON (ser.tm = {table}.{time_column})
    ORDER BY time
), rec AS (
    SELECT
        t_from AS gap_start, t_from-t_interval AS gap_end
    FROM input
    UNION
    SELECT
        gap_start,
        COALESCE((SELECT time-t_interval FROM filled
            WHERE {test_column} IS NOT NULL AND time > gap_start LIMIT 1),t_to) AS gap_end
    FROM (
        SELECT
            (SELECT time FROM filled WHERE {test_column} IS NULL AND time > gap_end LIMIT 1) AS gap_start
        FROM rec, input
        WHERE gap_end < t_to
    ) r, input )
SELECT {", ".join([f"EXTRACT(EPOCH FROM {f})::integer" if return_epoch else f for f in ["gap_start", "gap_end"]])}
FROM rec WHERE gap_end >= gap_start;'''

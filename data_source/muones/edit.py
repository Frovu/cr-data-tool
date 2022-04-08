from data_source.muones.db_proxy import pg_conn, remove_spikes, _table, _table_cond
from threading import Timer
import logging

SESSION_TIMEOUT = 3 * 60
active_uid = None
active_timer = None

def _close_session():
    global active_uid, active_timer
    active_uid = None
    active_timer = None

def _timeout():
    logging.info(f'Edit session timed out for uid={active_uid}')
    pg_conn.rollback()
    _close_session()

def _in_edit_session(uid):
    global active_uid, active_timer
    if active_uid == uid:
        active_timer.cancel()
    elif active_uid:
        return False
    active_uid = uid
    active_timer = Timer(SESSION_TIMEOUT, _timeout)
    return True

def _channel_condition(station, channel):
    if channel.lower() == 'all':
        return f'ANY (SELECT id FROM muon_channels WHERE station_name = %s)', [station]
    else:
        return f'(SELECT id FROM muon_channels WHERE station_name = %s AND channel_name = %s)', [station, channel]

def despike_auto(uid, station, channel, period):
    if not _in_edit_session(uid):
        return False, 0
    with pg_conn.cursor() as cursor:
        cond, vals = _channel_condition(station, channel)
        cursor.execute(remove_spikes(_table(period), cond), vals)
        rowcount = cursor.rowcount
    return True, rowcount

def despike_manual(uid, station, channel, period, timestamp):
    if not _in_edit_session(uid):
        return False, 0
    with pg_conn.cursor() as cursor:
        cond, vals = _channel_condition(station, channel)
        cursor.execute(f'''UPDATE {_table(period)} SET source = -1, corrected = NULL
        WHERE time = to_timestamp({timestamp}) AND channel = {cond}''', vals)
        rowcount = cursor.rowcount
    return True, rowcount

def close_session(uid, rollback):
    global active_uid, active_timer
    authorized = active_uid == uid
    if authorized:
        if rollback:
            pg_conn.rollback()
        else:
            pg_conn.commit()
        active_timer.cancel()
        _close_session()
    return authorized

def clear(station, channel, period):
    cond, vals = _channel_condition(station, channel)
    with pg_conn.cursor() as cursor:
        cursor.execute(f'DELETE FROM {_table(period)} WHERE channel = {cond}', vals)
        cursor.execute(f'DELETE FROM {_table_cond(period)} WHERE station = {cond}', vals)
        pg_conn.commit()

from data_source.muones.db_proxy import pg_conn, remove_spikes, _table, _table_cond
from threading import Timer

SESSION_TIMEOUT = 5 * 60
active_uid = None
active_timer = None

def _close_session():
    active_uid = None
    active_timer = None

def _timeout():
    pg_conn.rollback()
    _close_session()

def _in_edit_session(uid):
    if active_uid == uid:
        active_timer.cancel()
    elif active_uid:
        return False
    active_uid = uid
    active_timer = Timer(SESSION_TIMEOUT, _timeout)
    return True

def _channel_condition(station, channel):
    if channel.lower() == 'all':
        return f'IN (SELECT id FROM muon_channels WHERE station_name = {station})'
    else:
        return f'(SELECT id FROM muon_channels WHERE station_name = {station} AND channel_name = {channel})'

def despike_auto(uid, station, channel, period):
    if not _in_edit_session(uid):
        return False, 0
    with pg_conn.cursor() as cursor:
        cursor.execute(remove_spikes(_table(period), _channel_condition(station, channel)))
        rowcount = cursor.rowcount
    return True, rowcount

def despike_manual(uid, station, channel, period, timestamp):
    if not _in_edit_session(uid):
        return False, 0
    with pg_conn.cursor() as cursor:
        cursor.execute(f''''UPDATE {_table(period)} SET source = -1, corrected = NULL
        WHERE time = to_timestamp({timestamp}) AND channel = {_channel_condition(station, channel)}''')
        rowcount = cursor.rowcount
    return True, rowcount

def close_session(uid, commit=False):
    if active_uid == uid:
        if commit:
            pg_conn.commit()
        else:
            pg_conn.rollback()
        _close_session()
    return active_uid == uid

def clear(station, channel, period):
    channel_cond = _channel_condition(station, channel)
    with pg_conn.cursor() as cursor:
        cursor.execute(f'DELETE FROM {_table(period)} WHERE channel = {channel_cond}')
        cursor.execute(f'DELETE FROM {_table_cond(period)} WHERE station = {channel_cond}')
        pg_conn.commit()

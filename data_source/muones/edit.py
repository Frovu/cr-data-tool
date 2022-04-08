from data_source.muones.db_proxy import pg_conn, remove_spikes
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

def despike_auto(uid, channel=None):
    if not _in_edit_session(uid):
        return False, 0
    with pg_conn.cursor() as cursor:
        cursor.execute(remove_spikes(_table(channel.period), channel and channel.id))
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

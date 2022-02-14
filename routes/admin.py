import os
import gzip
import logging
import traceback
from flask import Blueprint, request
from core import permissions
from core import sql_queries
pg_conn = permissions.pg_conn

bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@bp.before_request
@permissions.require('ADMIN', 'OVERRIDE')
def app_auth():
    pass

@bp.route('/stats')
def register():
    try:
        args = request.args
        t_from = int(args.get('from'))
        t_to = args.get('to') and int(args.get('to'))
        interval = args.get('period') or '1 hour'
        types = ['query_accepted', 'get_result']
        with pg_conn.cursor() as cur:
            q = ', '.join([f'COUNT(*) FILTER (WHERE type = \'{t}\')' for t in types])
            cur.execute(sql_queries.aggregate_periods(t_from, t_to, interval, 'action_log', q))
            res = cur.fetchall()
        return { "data": res, "fields": ["time"] + types }
    except ValueError:
        return {}, 400
    except Exception:
        logging.info(f'exc in admin/stats: {traceback.format_exc()}')
        return {}, 500

@bp.route('/listUsers')
def listu():
    with pg_conn.cursor() as cur:
        cur.execute('SELECT login FROM users ORDER BY uid')
        return { "list": cur.fetchall() }

@bp.route('/user')
def user():
    with pg_conn.cursor() as cur:
        cur.execute('SELECT uid FROM users WHERE login = %s', [request.args.get('username')])
        res = cur.fetchall()
        if len(res) < 1:
            return {}, 404
        return permissions.list(res[0])

def editPermissions(action):
    flag = request.args.get('flag', '').upper()
    target = request.args.get('target', '').upper()
    if action == 'remove' and not target:
        target = 'OVERRIDE'
    if not flag or not target:
        return {}, 400
    if flag not in permissions.ALLOWED_TYPES:
        return {}, 403
    with pg_conn.cursor() as cur:
        cur.execute('SELECT uid FROM users WHERE login = %s', [request.args.get('username')])
        res = cur.fetchall()
        if len(res) < 1:
            return {}, 404
        uid = res[0]
        if action == 'add':
            res = cur.fetchall()
            q = 'INSERT INTO permissions VALUES (%s, %s, %s)'
            vals = [ uid, flag, target]
            cur.execute('SELECT uid FROM permissions WHERE uid = %s AND flag = %s AND target = %s', vals)
            if len(cur.fetchall()) > 0:
                return {}, 409
        else:
             q = 'DELETE FROM permissions WHERE uid = %s AND flag = %s'
             vals = [ uid, flag ]
             if target != 'OVERRIDE':
                q += 'AND target = %s'
                vals.append(target)
        cur.execute(q, vals)
        return {}, 200

@bp.route('/permissions/add')
def allow():
    return editPermissions('add')

@bp.route('/permissions/remove')
def forbid():
    return editPermissions('remove')

@bp.route('/logs')
def readlog():
    file_arg = request.args.get('file', '')
    level = request.args.get('file', '').upper()
    if file_arg:
        file = next((f for f in os.listdir('logs') if file_arg in f), None)
        if not file:
            return 'Not found: '+file_arg
    else:
        file = 'crdt.log'
    with gzip.open('logs/'+file, 'rb') if '.gz' in file else open('logs/'+file, 'rb') as f:
        text = f.read().decode()
    return f'''<html style="font-size: 13; font-family: monospace; background-color: rgb(25,5,25); color: darkgray;">
<head><title>{file}</title></head>
<plaintext>'''+text

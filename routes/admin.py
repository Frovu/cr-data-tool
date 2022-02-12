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

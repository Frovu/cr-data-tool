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
        period = int(args.get('period')) if args.get('period') else 3600
        with pg_conn.cursor() as cur:
            q = 'COUNT(*)'
            cur.execute(sql_queries.stack_periods(t_from, t_to, period, table, q))
            res = cursor.fetchall()
            print(res)
        return { "data": "" }
    except ValueError:
        return {}, 400
    except Exception:
        logging.error(f'exc in admin/stats: {traceback.format_exc()}')
        return {}, 500

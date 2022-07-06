from flask import Blueprint, request, session
from core import permissions
from core.utils import route_shielded
bp = Blueprint('neutron', __name__, url_prefix='/api/neutron')

from datetime import datetime, timezone
from data_source.neutron import circles

TRIM_PAST = datetime(1990, 1, 1).replace(tzinfo=timezone.utc).timestamp()
MAX_LEN_H = 30 * 24

@bp.route('/circles', methods=['GET'])
@route_shielded
def get_circles():
    t_from = int(request.args.get('from', ''))
    t_to = int(request.args.get('to', ''))
    exclude = request.args.get('exclude')
    exclude = exclude.split(',') if exclude else []
    trim_past, trim_future = TRIM_PAST, datetime.now().timestamp()
    t_from = t_from if t_from > trim_past else trim_past
    t_to = t_to if t_to < trim_future else trim_future
    trim_len = t_to - MAX_LEN_H * 3600
    t_from = t_from if t_from > trim_len else trim_len
    if t_to - t_from < 86400:
        raise ValueError()

    body = circles.get(t_from, t_to, exclude)
    body['status'] = 'ok'
    permissions.log_action('get_result', 'neutron/circle', f'{t_from}')
    return body

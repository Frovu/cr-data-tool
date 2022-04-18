from flask import Blueprint, request, session
from core import permissions
from core.utils import route_shielded
bp = Blueprint('neutron', __name__, url_prefix='/api/neutron')

from datetime import datetime
from data_source.neutron import circles

@bp.route('')
@route_shielded
def muon_corrected():
    t_from = int(request.args.get('from', ''))
    t_to = int(request.args.get('to', ''))
    trim_past, trim_future = datetime.timestamp(), datetime.now().timestamp()
    t_from = t_from if t_from > trim_past else trim_past
    t_to = t_to if t_to < trim_future else trim_future

    body = circles.get(t_from, t_to)
    body['status'] = 'ok'
    permissions.log_action('get_result', 'neutron/circle', f'{t_from}')
    return body

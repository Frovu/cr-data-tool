from flask import Blueprint, request

from omni import database
from routers.utils import route_shielded, require_auth

bp = Blueprint('omni', __name__, url_prefix='/api/omni')

@bp.route('', methods=['GET'])
@route_shielded
def get_result():
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	query = request.args.get('query')
	res, fields = database.select([t_from, t_to], query.split(',') if query else None)
	return { 'fields': fields, 'rows': res }

@bp.route('/fetch', methods=['POST'])
@require_auth
@route_shielded
def fetch():
	t_from = int(request.json.get('from'))
	t_to = int(request.json.get('to'))
	src = request.json.get('source', 'omniweb')
	group = request.json.get('group', 'all')
	ovw = request.json.get('overwrite', 'false') == 'true'

	count = database.obtain(src, [t_from, t_to], group, ovw)
	return { 'message': f'Upserted [{count}]' }
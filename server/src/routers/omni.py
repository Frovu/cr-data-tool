from flask import Blueprint, request

from omni import database
from routers.utils import route_shielded, require_auth

bp = Blueprint('omni', __name__, url_prefix='/api/omni')

@bp.route('', methods=['GET'])
@route_shielded
def get_result():
	t_from = int(request.args.get('from', 0))
	t_to = int(request.args.get('to', 86400))
	query = request.args.get('query')
	res, fields = database.select([t_from, t_to], query.split(',') if query else None)
	return { 'fields': fields, 'rows': res }

@bp.route('/ensure', methods=['POST'])
@require_auth
@route_shielded
def ensure_trust():
	t_from = request.json.get('from')
	t_to = request.json.get('to')
	return database.ensure_prepared([t_from, t_to], trust=True)

@bp.route('/ensure', methods=['GET'])
@route_shielded
def ensure():
	if 'from' not in request.args:
		return database.dump_info
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	if t_to < t_from:
		raise ValueError('Negative interval')
	return database.ensure_prepared([t_from, t_to])

@bp.route('/fetch', methods=['POST'])
@require_auth
@route_shielded
def fetch():
	t_from = int(request.json.get('from'))
	t_to = int(request.json.get('to'))
	src = request.json.get('source', 'omniweb').lower()
	group = request.json.get('group', 'all').lower()
	ovw = request.json.get('overwrite', False)

	if group == 'geomag' and src not in ['geomag', 'omniweb']:
		return { 'message': 'Geomag can only be fetched from Geomag' }

	count = database.obtain(src, [t_from, t_to], group, ovw)
	return { 'message': f'Upserted [{count} h] of *{group} from {src}' }

@bp.route('/remove', methods=['POST'])
@require_auth
@route_shielded
def remove():
	t_from = int(request.json.get('from'))
	t_to = int(request.json.get('to'))
	group = request.json.get('group', 'all').lower()

	count = database.remove([t_from, t_to], group)
	return { 'message': f'Removed [{count}] hour{"s" if count == 1 else ""} *{group}' }
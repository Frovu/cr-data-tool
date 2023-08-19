from flask import Blueprint, request

from omni import database
from routers.utils import route_shielded

bp = Blueprint('omni', __name__, url_prefix='/api/omni')

@bp.route('/', methods=['GET'])
@route_shielded
def get_result():
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	query = request.args.get('query')
	res, fields = database.select([t_from, t_to], query.split(',') if query else None)
	return { "fields": fields, "rows": res }
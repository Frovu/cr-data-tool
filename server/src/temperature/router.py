from datetime import datetime
from flask import Blueprint, request

from temperature import ncep
from utils import route_shielded

bp = Blueprint('temperature', __name__, url_prefix='/api/temperature')

@bp.route('', methods=['GET'])
@route_shielded
def get_result():
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	lat = float(request.args.get('lat'))
	lon = float(request.args.get('lon'))
	dt_interval = [datetime.utcfromtimestamp(t) for t in [t_from, t_to]]
	if progress := ncep.ensure_downloaded(dt_interval):
		return { 'status': 'busy', 'downloading': progress }
	return { 'status': 'ok' }
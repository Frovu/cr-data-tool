from flask import Blueprint, request

from temperature import ncep
from utils import route_shielded
import numpy as np

bp = Blueprint('temperature', __name__, url_prefix='/api/temperature')

@bp.route('', methods=['GET'])
@route_shielded
def get_result():
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	lat = float(request.args.get('lat'))
	lon = float(request.args.get('lon'))
	progress, data = ncep.obtain([t_from, t_to], lat, lon)
	if progress:
		return { 'status': 'busy', 'downloading': progress }
	return {
		'status': 'ok',
		'fields': ['time', 't_mass_average', *[f't_{l}mb' for l in ncep.LEVELS]],
		'coords': { 'lat': lat, 'lon': lon },
		'rows': np.where(np.isnan(data), None, np.round(data, 2)).tolist() if data is not None else None
	}

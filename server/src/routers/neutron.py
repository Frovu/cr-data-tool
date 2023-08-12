from flask import Blueprint, request
from neutron import neutron, corrections
from routers.utils import route_shielded

bp = Blueprint('neutron', __name__, url_prefix='/api/neutron')

@bp.route('', methods=['GET'])
@route_shielded
def get_neutron():
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	sts_req = request.args.get('stations', 'all').lower()
	all_stations = neutron.get_stations(ids=True)
	stations = all_stations if sts_req == 'all' else [s for s in all_stations if s.lower() in sts_req.split(',')]
	if not len(stations):
		raise ValueError('No stations match query')
	if t_from >= t_to:
		raise ValueError('Bad interval')
	rows, fields = neutron.fetch((t_from, t_to), stations)
	return { 'fields': fields, 'rows': rows }

@bp.route('/minutes', methods=['GET'])
@route_shielded
def get_minutes():
	timestamp = int(request.args.get('timestamp'))
	station = request.args.get('station') # FIXME !!
	return { 'station': station, 'minutes': corrections.get_minutes(station, timestamp) }
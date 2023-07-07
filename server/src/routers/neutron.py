from flask import Blueprint, request
from neutron import neutron
from routers.utils import route_shielded

bp = Blueprint('neutron', __name__, url_prefix='/api/neutron')

@bp.route('/', methods=['GET'])
@route_shielded
def get_neutron():
	from datetime import datetime, timezone
	neutron._obtain_group([
		datetime(2023, 7, 6, 12).replace(tzinfo=timezone.utc).timestamp(),
		datetime(2023, 7, 7, 0).replace(tzinfo=timezone.utc).timestamp(),
	], True)
	return 'Hello World'
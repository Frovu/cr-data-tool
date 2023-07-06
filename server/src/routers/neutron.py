from flask import Blueprint, request

from routers.utils import route_shielded

bp = Blueprint('neutron', __name__, url_prefix='/api/neutron')

@bp.route('/', methods=['GET'])
@route_shielded
def get_neutron():
	return 'Hello World'
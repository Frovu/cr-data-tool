from flask import Blueprint, request

from muon.database import select, obtain_all
from utils import route_shielded, require_auth
import numpy as np

bp = Blueprint('muon', __name__, url_prefix='/api/muon')

@bp.route('', methods=['GET'])
@route_shielded
def select_result():
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	experiment = request.args.get('experiment')
	channel = request.args.get('cahnnel', 'V')
	query = request.args.get('query', 'revised').split(',')
	rows, fields = select(t_from, t_to, experiment, channel, query)
	return { 'fields': fields, 'rows': rows }

@bp.route('obtain', methods=['POST'])
@route_shielded
@require_auth
def do_obtain_all():
	t_from = int(request.json.get('from'))
	t_to = int(request.json.get('to'))
	experiment = request.json.get('experiment')
	return obtain_all(t_from, t_to, experiment)

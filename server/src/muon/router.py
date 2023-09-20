from flask import Blueprint, request

from muon.database import select_experiments, obtain_all, do_revision
from muon.corrections import select_with_corrected
from utils import route_shielded, require_auth, msg

bp = Blueprint('muon', __name__, url_prefix='/api/muon')

@bp.route('experiments', methods=['GET'])
@route_shielded
def do_select_experiments():
	return { 'experiments': select_experiments() }

@bp.route('', methods=['GET'])
@route_shielded
def do_select_result():
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	experiment = request.args.get('experiment')
	channel = request.args.get('cahnnel', 'V')
	query = request.args.get('query', 'corrected').split(',')
	rows, fields = select_with_corrected(t_from, t_to, experiment, channel, query)
	return { 'fields': fields, 'rows': rows }

@bp.route('obtain', methods=['POST'])
@route_shielded
@require_auth
def do_obtain_all():
	t_from = int(request.json.get('from'))
	t_to = int(request.json.get('to'))
	experiment = request.json.get('experiment')
	return obtain_all(t_from, t_to, experiment)

@bp.route('compute', methods=['POST'])
@route_shielded
@require_auth
def do_comp_corr():
	t_from = int(request.json.get('from'))
	t_to = int(request.json.get('to'))
	experiment = request.json.get('experiment')
	channel = request.json.get('channel', 'V')
	do_compute(t_from, t_to, experiment, channel)
	return msg('OK')

@bp.route('revision', methods=['POST'])
@route_shielded
@require_auth
def do_insert_revision():
	t_from = int(request.json.get('from'))
	t_to = int(request.json.get('to'))
	experiment = request.json.get('experiment')
	channel = request.json.get('channel')
	action = request.json.get('action')
	do_revision(t_from, t_to, experiment, channel, action)
	return msg('OK')
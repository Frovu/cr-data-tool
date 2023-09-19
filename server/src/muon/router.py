from flask import Blueprint, request

from muon.database import select, select_experiments, obtain_all
from muon.corrections import do_compute, get_predicted
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
	query = request.args.get('query', 'revised').split(',')
	rows, fields = select(t_from, t_to, experiment, channel, query)
	return { 'fields': fields, 'rows': rows }

@bp.route('predicted', methods=['GET'])
@route_shielded
def select_predicted_result():
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	experiment = request.args.get('experiment')
	channel = request.args.get('cahnnel', 'V')
	rows = get_predicted(t_from, t_to, experiment, channel)
	return { 'fields': ['time', 'gsm_v'], 'rows': rows }

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
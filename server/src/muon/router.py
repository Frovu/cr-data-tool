from flask import Blueprint, request

from muon.database import select
from utils import route_shielded
import numpy as np

bp = Blueprint('muon', __name__, url_prefix='/api/muon')

@bp.route('', methods=['GET'])
@route_shielded
def select_result():
	t_from = int(request.args.get('from'))
	t_to = int(request.args.get('to'))
	station = request.args.get('station')
	channel = request.args.get('cahnnel', 'V')
	query = request.args.get('fields', 'revised').split(',')
	rows, fields = select(t_from, t_to, station, channel)
	return { 'fields': fields, 'rows': rows }


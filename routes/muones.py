import data_source.muones.data as muones
from flask import Blueprint, request
from datetime import datetime
import logging
import traceback

bp = Blueprint('muones', __name__, url_prefix='/api/muones')

@bp.route('/raw')
def get():
    try:
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        station = request.args.get('station', '')
    except ValueError:
        return {}, 400
    try:
        status, data = muones.get_everything(station, t_from, t_to)
    except Exception:
        logging.error(f'Exception in muones.get: {traceback.format_exc()}')
        return {}, 500
    body = { "status": status }
    if status == 'ok':
        body["fields"] = data[1]
        body["data"] = data[0]
    # else:
    #     if status == 'busy' and data:
    #         body["download"] = data
    return body

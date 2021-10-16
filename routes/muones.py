import data_source.muones.data as muones
from flask import Blueprint, request
from datetime import datetime
import logging
import traceback

bp = Blueprint('muones', __name__, url_prefix='/api/muones')

@bp.route('/raw')
def raw():
    try:
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        station = request.args.get('station', '')
        status, data = muones.get_raw(station, t_from, t_to)
        body = { "status": status }
        if status == 'ok':
            body["fields"] = data[1]
            body["data"] = data[0]
        return body
    except ValueError:
        return {}, 400
    except Exception:
        logging.error(f'exc in muones/raw: {traceback.format_exc()}')
        return {}, 500

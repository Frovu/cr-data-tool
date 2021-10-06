import data_source.muones.data as muones
from flask import Blueprint, request
from datetime import datetime
import logging
import traceback

bp = Blueprint('muones', __name__, url_prefix='/api/muones')

@bp.route('/')
def get():
    try:
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        station = request.args.get('station', '')
        if not station:
            lat = float(request.args.get('lat', ''))
            lon = float(request.args.get('lon', ''))
            station = muones.station(lat, lon)
            if not station:
                return {}, 404
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

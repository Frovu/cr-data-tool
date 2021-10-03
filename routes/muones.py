import data_source.muones.data as muones
from flask import Blueprint, request
from datetime import datetime

bp = Blueprint('muones', __name__, url_prefix='/api/muones')

@bp.route('/')
def get():
    try:
        dt_from = datetime.fromtimestamp(int(request.args.get('from', '')))
        dt_to = datetime.fromtimestamp(int(request.args.get('to', '')))
        station = request.args.get('station', '')
        if not station:
            lat = float(request.args.get('lat', ''))
            lon = float(request.args.get('lon', ''))
            station = muones.station(lat, lon)
            if not station:
                return {}, 404
    except ValueError:
        return {}, 400
    return muones.get_everything(station, dt_from, dt_to)

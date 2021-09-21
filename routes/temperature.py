import data_source.temperature_model.temperature as temperature
from flask import Blueprint, request
from datetime import datetime, timezone

bp = Blueprint('temp', __name__, url_prefix='/api/temp')

@bp.route('/')
def get():
    try:
        dt_from = datetime.fromtimestamp(int(request.args.get('from', '')))
        dt_to = datetime.fromtimestamp(int(request.args.get('to', '')))
        lat = float(request.args.get('lat', ''))
        lon = float(request.args.get('lon', ''))
    except ValueError:
        return {}, 400
    status, data = temperature.get(lat, lon, dt_from, dt_to)
    body = { "status": status }
    if status != 'ok':
        if status == 'busy' and data:
            body["download"] = data
        return body
    body["fields"] = ['time'] + temperature.proxy.LEVELS
    body["data"] = data
    return body


@bp.route('/stations')
def stations():
    return { 'list': temperature.get_stations() }

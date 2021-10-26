import data_source.temperature_model.temperature as t_model
import data_source.stations_meteo.data as t_stations
from flask import Blueprint, request
from datetime import datetime

bp = Blueprint('temperature', __name__, url_prefix='/api/temperature')

@bp.route('')
def get():
    try:
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        dt_from = datetime.utcfromtimestamp(t_from)
        dt_to = datetime.utcfromtimestamp(t_to)
        lat = float(request.args.get('lat', ''))
        lon = float(request.args.get('lon', ''))
    except ValueError:
        return {}, 400
    only = request.args.get('only', '')
    if only == 'model':
        status, data = t_model.get(lat, lon, dt_from, dt_to)
    else:
        status, data = t_stations.get_with_model(lat, lon, t_from, t_to)
    body = { "status": status }
    if status != 'ok':
        if status in ['busy', 'failed'] and data:
            body["info"] = data
        return body
    body["fields"] = data[1]
    body["data"] = data[0]
    return body


@bp.route('/stations')
def stations():
    return { 'list': t_model.get_stations() }

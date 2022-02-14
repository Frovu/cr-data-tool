import data_source.temperature_model.temperature as t_model
import data_source.temperature_model.proxy as database
import data_source.stations_meteo.data as t_stations
from flask import Blueprint, request
from datetime import datetime
from core import permissions
import logging

bp = Blueprint('temperature', __name__, url_prefix='/api/temperature')

@bp.route('')
def get():
    try:
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        lat = float(request.args.get('lat', ''))
        lon = float(request.args.get('lon', ''))
    except ValueError:
        return {}, 400
    only = request.args.get('only', '')
    if only == 'model':
        status, data = t_model.get(lat, lon, t_from, t_to)
    elif only == 'model_avg':
        status, data = t_model.get(lat, lon, t_from, t_to, only=['mass_average'])
    else:
        status, data = t_stations.get_with_model(lat, lon, t_from, t_to)
    body = { "status": status }
    if status != 'ok':
        if status in ['busy', 'failed'] and data:
            body["info"] = data
        elif status == 'accepted':
            permissions.log_action('query_accepted', 'temperature', f'{lat},{lon}')
        return body
    permissions.log_action('get_result', 'temperature', f'{lat},{lon}')
    body["fields"] = data[1]
    body["data"] = data[0]
    return body

@bp.route('/stations', methods=['GET'])
def stations():
    return { 'list': t_model.get_stations() }

@bp.route('/delete')
@permissions.require('DELETE_DATA', 'TEMPERATURE')
def erase():
    try:
        lat = float(request.args.get('lat', ''))
        lon = float(request.args.get('lon', ''))
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        database.delete(lat, lon, t_from, t_to)
        permissions.log_action('delete_data', 'temperature', f'{lat},{lon}')
        return {}
    except ValueError:
        return {}, 400
    except Exception as e:
        logging.error(f'ERROR in temperature/delete {e}')
        return {}, 500

@bp.route('/stations', methods=['POST'])
@permissions.require('ADMIN', 'TEMPERATURE')
def erase():
    try:
        lat = float(request.args.get('lat', ''))
        lon = float(request.args.get('lon', ''))
        name = request.args.get('name')
        description = request.args.get('description')
        if not name: raise ValueError()
        if database.get_station(lat, lon):
            database.edit_station(lat, lon, name, description)
            permissions.log_action('edit_station', 'temperature', f'{lat},{lon}')
        else:
            database.create_station(lat, lon, name, description)
            permissions.log_action('create_station', 'temperature', f'{lat},{lon}')
        return {}
    except ValueError:
        return {}, 400
    except Exception as e:
        logging.error(f'ERROR in temperature/station {e}')
        return {}, 500

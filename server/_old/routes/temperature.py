import data_source.atmosphere.temperature as t_model
import data_source.atmosphere.ground_flux as gflux
import data_source.atmosphere.proxy as database
import data_source.stations_meteo.data as t_stations
from flask import Blueprint, request
from datetime import datetime
from core import permissions
from core.utils import route_shielded
import logging, numpy

bp = Blueprint('temperature', __name__, url_prefix='/api/temperature')

@bp.route('')
@route_shielded
def get():
    t_from = int(request.args.get('from', ''))
    t_to = int(request.args.get('to', ''))
    lat = float(request.args.get('lat', ''))
    lon = float(request.args.get('lon', ''))
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
    res = numpy.round(numpy.array(data[0], dtype='float'), 2)
    body["data"] = numpy.where(numpy.isnan(res), None, res).tolist()
    return body

@bp.route('/gflux', methods=['GET'])
@route_shielded
def get_gflux():
    t_from = int(request.args.get('from', ''))
    t_to = int(request.args.get('to', ''))
    lat = float(request.args.get('lat', ''))
    lon = float(request.args.get('lon', ''))
    res = gflux.get(lat, lon, t_from, t_to)
    body = { "status": "ok", "data": numpy.where(numpy.isnan(res), None, res).tolist() }
    return body

@bp.route('/stations', methods=['GET'])
@route_shielded
def stations():
    return { 'list': database.get_stations() }

@bp.route('/delete')
@permissions.require('DELETE_DATA', 'TEMPERATURE')
@route_shielded
def erase_temperature():
    lat = float(request.args.get('lat', ''))
    lon = float(request.args.get('lon', ''))
    t_from = int(request.args.get('from', ''))
    t_to = int(request.args.get('to', ''))
    database.delete(lat, lon, t_from, t_to)
    permissions.log_action('delete_data', 'temperature', f'{lat},{lon}')
    return {}

@bp.route('/stations', methods=['POST'])
@permissions.require('ADMIN', 'TEMPERATURE')
@route_shielded
def station_edit():
    lat = float(request.values.get('lat', ''))
    lon = float(request.values.get('lon', ''))
    name = request.values.get('name')
    description = request.values.get('description')
    if not name: raise ValueError()
    if database.get_station(lat, lon):
        database.edit_station(lat, lon, name, description)
        permissions.log_action('edit_station', 'temperature', f'{lat},{lon},{name}')
    else:
        database.create_station(lat, lon, name, description)
        permissions.log_action('create_station', 'temperature', f'{lat},{lon},{name}')
    return {}

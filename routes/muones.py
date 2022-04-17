import data_source.muon.data as muones
import data_source.muon.edit as edit
import data_source.stations_meteo.pressure as meteo
from flask import Blueprint, request, session
from datetime import datetime
from core import permissions
from core.utils import route_shielded
import logging
import traceback

bp = Blueprint('muones', __name__, url_prefix='/api/muones')

# @bp.before_request
# @permissions.require('USE_APPLICATION', 'MUON')
# def app_auth():
#     pass

@bp.route('/stations')
def stations():
    return { 'list': muones.stations() }

@bp.route('')
@route_shielded
def muon_corrected():
    t_from = int(request.args.get('from', ''))
    t_to = int(request.args.get('to', ''))
    station = request.values.get('station')
    channel = request.values.get('channel', 'V')
    period = int(request.values.get('period', 3600))
    temp_src = request.args.get('tmode', 'T_m')
    coefs = request.args.get('coefs', 'saved')
    if period not in [60, 3600] or coefs not in ['saved', 'recalc', 'retain'] or temp_src not in ['T_m', 'T_eff']:
        raise ValueError()
    if coefs == 'retain':
        if not permissions.check('ADMIN', 'MUONS'):
            return {}, 403
    status, data = muones.get_corrected(station, t_from, t_to, period, channel, coefs, temp_src)
    body = { "status": status }
    if status == 'ok':
        body["info"] = data[2]
        body["fields"] = data[1]
        body["data"] = data[0]
        if coefs == 'retain':
            permissions.log_action('update_coefs', 'muones/corrected', f'{station}/{channel}')
        permissions.log_action('get_result', 'muones/corrected', f'{station}/{channel}')
    elif status in ['busy', 'failed'] and data:
        body["info"] = data
    elif status == 'accepted':
        permissions.log_action('query_accepted', 'muones/corrected', f'{station}/{channel}')
    return body

@bp.route('/clean', methods=['POST'])
@permissions.require('DELETE_DATA', 'MUONS')
@route_shielded
def muon_erase():
    station = request.values.get('station')
    channel = request.values.get('channel', 'V')
    period = int(request.values.get('period', 3600))
    edit.clear(station, channel, period)
    permissions.log_action('delete_data', 'muons', f'{station}/{channel}')
    return {}

@bp.route('/despike', methods=['POST'])
@permissions.require('DELETE_DATA', 'MUONS')
@route_shielded
def muon_despike():
    station = request.values.get('station')
    channel = request.values.get('channel', 'V')
    period = int(request.values.get('period', 3600))
    status, count = edit.despike_auto(session.get('uid'), station, channel, period)
    if not status:
        return { 'message': 'another session is active'}, 409
    permissions.log_action('despike', 'muons', f'{station}/{channel}')
    return { 'count': count }

@bp.route('/fix', methods=['POST'])
@permissions.require('DELETE_DATA', 'MUONS')
@route_shielded
def muon_fix():
    station = request.values.get('station')
    channel = request.values.get('channel', 'V')
    period = int(request.values.get('period', 3600))
    timestamp = int(request.values.get('timestamp', ''))
    status, count = edit.despike_manual(session.get('uid'), station, channel, period, timestamp)
    if not status:
        return { 'message': 'another session is active'}, 409
    permissions.log_action('fix', 'muons', f'{station}/{channel}')
    return { 'count': count }

@bp.route('/commit', methods=['POST'])
@permissions.require('DELETE_DATA', 'MUONS')
@route_shielded
def muon_commit_edit():
    rollback = request.values.get('rollback', False)
    if not edit.close_session(session.get('uid'), rollback):
        return { 'message': 'not in a session'}, 400
    permissions.log_action('commit_edit', 'muons', f'{"rollback" if rollback else "commit"}')
    return { }

@bp.route('/raw')
@route_shielded
def muon_raw():
    t_from = int(request.args.get('from', ''))
    t_to = int(request.args.get('to', ''))
    period = int(request.values.get('period', 3600))
    station = request.args.get('station')
    if period not in [60, 3600]:
        raise ValueError()
    status, data = muones.get_raw(station, t_from, t_to, period)
    body = { "status": status }
    if status == 'ok':
        body["fields"] = data[1]
        body["data"] = data[0]
        permissions.log_action('get_result', 'muones/raw', station)
    elif status in ['busy', 'failed'] and data:
        body["info"] = data
    return body

@bp.route('/correlation')
@route_shielded
def muon_correlation():
    t_from = int(request.args.get('from', ''))
    t_to = int(request.args.get('to', ''))
    period = int(request.args.get('period')) if request.args.get('period') else 3600
    against = request.args.get('against', '') or 'T_m'
    station = request.args.get('station', '')
    channel = request.args.get('channel', '')
    only = request.args.get('only', '')
    if period not in [60, 3600] or against not in ['pressure', 'T_eff', 'T_m', 'all']:
        raise ValueError()
    status, data = muones.get_correlation(station, t_from, t_to, period,
        against=against, channel=channel, only=only)
    body = { "status": status }
    if status == 'ok':
        permissions.log_action('get_result', 'muones/correlation', station)
        body["data"] = data
    elif status in ['busy', 'failed'] and data:
        body["info"] = data
    return body

@bp.route('/pressure')
@route_shielded
def pressure():
    t_from = int(request.args.get('from', ''))
    t_to = int(request.args.get('to', ''))
    station = request.args.get('station', '')
    data = meteo.get(station, t_from, t_to)
    if data:
        permissions.log_action('get_result', 'muones/pressure', station)
        return { "status": "ok", "data": data[0], "fields": data[1] }
    else:
        return { "status": "unknown" }

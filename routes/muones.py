import data_source.muones.data as muones
import data_source.stations_meteo.pressure as meteo
from flask import Blueprint, request
from datetime import datetime
from core import permissions
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
def corrected():
    try:
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        period = int(request.args.get('period')) if request.args.get('period') else 3600
        station = request.args.get('station', '')
        channel = request.args.get('channel', '') or 'V'
        coefs = request.args.get('coefs', '') or 'saved'
        if period not in [60, 3600]:
            raise ValueError()
        if coefs == 'retain':
            if not permissions.check('ADMIN', 'MUONS'):
                return {}, 403
        status, data = muones.get_corrected(station, t_from, t_to, period, channel, coefs)
        body = { "status": status }
        if status == 'ok':
            body["info"] = data[2]
            body["fields"] = data[1]
            body["data"] = data[0]
            if coefs == 'retain':
                permissions.log_action('update_coefs', 'muones/corrected', station)
            permissions.log_action('get_result', 'muones/corrected', station)
        elif status in ['busy', 'failed'] and data:
            body["info"] = data
        elif status == 'accepted':
            permissions.log_action('query_accepted', 'muones/corrected', station)
        return body
    except ValueError:
        return {}, 400
    except Exception:
        logging.error(f'exc in muones/corrected: {traceback.format_exc()}')
        return {}, 500

@bp.route('/clean', methods=['POST'])
@permissions.require('DELETE_DATA', 'MUONS')
def erase():
    try:
        station = request.values.get('station', '')
        channel = request.values.get('channel', '') or 'V'
        t_from = int(request.values.get('from', ''))
        t_to = int(request.values.get('to', ''))
        period = int(request.values.get('period')) if request.values.get('period') else 3600
        ch = muones.proxy.channel(station, channel, period)
        muones.proxy.clear(ch)
        permissions.log_action('delete_data', 'muons', f'{station}/{channel}')
        return {}
    except ValueError:
        print(traceback.format_exc())
        return {}, 400
    except Exception as e:
        logging.error(f'ERROR in muons/delete {e}')
        return {}, 500

@bp.route('/raw')
def raw():
    try:
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        period = int(request.args.get('period')) if request.args.get('period') else 3600
        station = request.args.get('station', '')
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
    except ValueError:
        return {}, 400
    except Exception:
        logging.error(f'exc in muones/raw: {traceback.format_exc()}')
        return {}, 500

@bp.route('/correlation')
def correlation():
    try:
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        period = int(request.args.get('period')) if request.args.get('period') else 3600
        against = request.args.get('against', '') or 'Tm'
        station = request.args.get('station', '')
        channel = request.args.get('channel', '')
        only = request.args.get('only', '')
        if period not in [60, 3600] or against not in ['pressure', 'Tm', 'T_m', 'all']:
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
    except ValueError:
        return {}, 400
    except Exception:
        logging.error(f'exc in muones/correlation: {traceback.format_exc()}')
        return {}, 500

@bp.route('/pressure')
def pressure():
    try:
        t_from = int(request.args.get('from', ''))
        t_to = int(request.args.get('to', ''))
        station = request.args.get('station', '')
        data = meteo.get(station, t_from, t_to)
        if data:
            permissions.log_action('get_result', 'muones/pressure', station)
            return { "status": "ok", "data": data[0], "fields": data[1] }
        else:
            return { "status": "unknown" }
    except ValueError:
        return {}, 400
    except Exception:
        logging.error(f'exc in muones/correlation: {traceback.format_exc()}')
        return {}, 500

import data_source.muones.data as muones
import data_source.stations_meteo.pressure as meteo
from flask import Blueprint, request
from datetime import datetime
import logging
import traceback

bp = Blueprint('muones', __name__, url_prefix='/api/muones')

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
        if period not in [60, 3600]:
            raise ValueError()
        status, data = muones.get_corrected(station, t_from, t_to, period)
        body = { "status": status }
        if status == 'ok':
            body["info"] = data[2]
            body["fields"] = data[1]
            body["data"] = data[0]
        return body
    except ValueError:
        return {}, 400
    except Exception:
        logging.error(f'exc in muones/corrected: {traceback.format_exc()}')
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
        against = request.args.get('against') or 'pressure'
        station = request.args.get('station', '')
        if period not in [60, 3600] or against not in ['pressure', 'Tm']:
            raise ValueError()
        status, data = muones.get_correlation(station, t_from, t_to, period, against)
        body = { "status": status }
        if status == 'ok':
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
            return { "status": "ok", "data": data[0], "fields": data[1] }
        else:
            return { "status": "unknown" }
    except ValueError:
        return {}, 400
    except Exception:
        logging.error(f'exc in muones/correlation: {traceback.format_exc()}')
        return {}, 500

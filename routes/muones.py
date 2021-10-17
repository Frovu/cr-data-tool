import data_source.muones.data as muones
from flask import Blueprint, request
from datetime import datetime
import logging
import traceback

bp = Blueprint('muones', __name__, url_prefix='/api/muones')

@bp.route('/stations')
def stations():
    return { 'list': muones.stations() }

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
        return body
    except ValueError:
        return {}, 400
    except Exception:
        logging.error(f'exc in muones/correlation: {traceback.format_exc()}')
        return {}, 500

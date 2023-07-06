import gzip, os
import logging
import logging.handlers

if not os.path.exists('log'):
    os.makedirs('log')
def rotator(source, dest):
    with open(source, "rb") as sf:
        data = sf.read()
        compressed = gzip.compress(data)
        with open(dest+'.gz', "wb") as df:
            df.write(compressed)
    os.remove(source)

formatter = logging.Formatter('%(asctime)s/%(levelname)s: %(message)s')
log_rotate = logging.handlers.TimedRotatingFileHandler('log/crdt.log', 'midnight')
log_rotate.rotator = rotator
log_rotate.setLevel(logging.DEBUG)
log_rotate.setFormatter(formatter)

sh = logging.StreamHandler()
sh.setFormatter(formatter)

logger = logging.getLogger('crdt')
logger.handlers = [ log_rotate, sh ]
logger.setLevel(logging.DEBUG)
logger.propagate = False

logging.getLogger('werkzeug').setLevel(logging.WARNING)
import requests
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('urllib3').propagate = False

logger.critical('STARTING SERVER')

from flask import Flask, send_file, session
from flask_session import Session
from flask_bcrypt import Bcrypt

app = Flask('crdt')
if hasattr(app, 'json'):
    app.json.sort_keys = False
else:
    app.config['JSON_SORT_KEYS'] = False

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_THRESHOLD'] = 32

Session(app)
bcrypt = Bcrypt(app)

from routers import neutron
app.register_blueprint(neutron.bp)

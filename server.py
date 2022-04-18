import gzip
import os
import logging
import logging.handlers

if not os.path.exists('logs'):
    os.makedirs('logs')
def rotator(source, dest):
    with open(source, "rb") as sf:
        data = sf.read()
        compressed = gzip.compress(data)
        with open(dest+'.gz', "wb") as df:
            df.write(compressed)
    os.remove(source)

formatter = logging.Formatter('%(asctime)s/%(levelname)s: %(message)s')
log_rotate = logging.handlers.TimedRotatingFileHandler('logs/crdt.log', 'midnight')
log_rotate.rotator = rotator
log_rotate.setLevel(logging.DEBUG)
log_rotate.setFormatter(formatter)

sh = logging.StreamHandler()
sh.setFormatter(formatter)

logger = logging.getLogger()
logger.handlers = [ log_rotate, sh ]
logger.setLevel(logging.DEBUG)

logging.getLogger('werkzeug').setLevel(logging.WARNING)
import requests
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('urllib3').propagate = False

logging.critical('STARTING SERVER')

from flask import Flask, send_file, session
from flask_session import Session
from flask_bcrypt import Bcrypt
app = Flask(__name__,
            static_url_path='',
            static_folder='static',)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_THRESHOLD'] = 32
Session(app)
bcrypt = Bcrypt(app)

from routes import temperature
from routes import neutron
from routes import muones
from routes import admin
from routes import auth
app.register_blueprint(temperature.bp)
app.register_blueprint(neutron.bp)
app.register_blueprint(muones.bp)
app.register_blueprint(admin.bp)
app.register_blueprint(auth.bp)

@app.route("/")
def index():
    return send_file('static/index.html')

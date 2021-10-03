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

from flask import Flask, send_file
from routes import temperature
from routes import muones
app = Flask(__name__,
            static_url_path='',
            static_folder='static',)
app.register_blueprint(temperature.bp)
app.register_blueprint(muones.bp)

@app.route("/")
def index():
    return send_file('static/index.html')

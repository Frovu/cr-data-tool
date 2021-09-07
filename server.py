from flask import Flask, send_file
from routes import temperature

app = Flask(__name__,
            static_url_path='',
            static_folder='static',)
app.register_blueprint(temperature.bp)

@app.route("/")
def index():
    return send_file('static/index.html')

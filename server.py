from flask import Flask
from routes import temperature

app = Flask(__name__)
app.register_blueprint(temperature.bp)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

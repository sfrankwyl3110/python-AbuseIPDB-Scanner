import os.path
from flask import Flask
import os

templates_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def create_app():
    app = Flask(__name__, template_folder=templates_path, static_folder=static_path)

    from wsgi_app.app.blueprints.general import bp_general
    app.register_blueprint(bp_general)

    return app

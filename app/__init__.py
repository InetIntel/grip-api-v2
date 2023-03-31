import os
import toml

from flask import Flask
from . import api_json

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='supersecret'
    )

    if test_config is None:
        app.config.from_file('config.toml', load=toml.load)
    else:
        app.config.from_mapping(test_config)

    app.register_blueprint(api_json.bp)
    return app



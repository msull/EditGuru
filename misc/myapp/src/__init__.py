from flask import Flask
from .blueprints.example import example_bp

def create_app():
    app = Flask(__name__)

    # Register the Blueprint
    app.register_blueprint(example_bp)

    return app
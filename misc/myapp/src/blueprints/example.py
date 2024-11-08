from flask import Blueprint

example_bp = Blueprint('example', __name__)

@example_bp.route('/example')
def example_route():
    return "Hello from the example blueprint!"
"""
Route modules for the Flask application
"""

import logging

from app.routes.main import main_bp
from app.routes.debug import debug_bp
from app.routes.health import health_bp

# Import API blueprint with absolute import for clarity and to avoid relative import pitfalls
try:
    from app.routes.api import api_bp
except Exception as e:
    logging.exception("Failed to import API blueprints: %s", e)
    # Define a minimal fallback blueprint to prevent hard crash; real endpoints won't be available
    from flask import Blueprint
    api_bp = Blueprint('api', __name__)


def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(debug_bp)
    app.register_blueprint(health_bp)
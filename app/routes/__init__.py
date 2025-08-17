"""
Route modules for the Flask application
"""

from .main import main_bp
from .api import api_bp
from .debug import debug_bp
from .health import health_bp

def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(debug_bp)
    app.register_blueprint(health_bp)
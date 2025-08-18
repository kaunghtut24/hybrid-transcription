"""
Flask application factory
"""

import os
import logging
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from .config import config
from .routes import register_blueprints
from .websocket import register_websocket_handlers

def create_app(config_name=None):
    """Create and configure the Flask application"""
    
    # Determine configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    # Create Flask app
    app = Flask(__name__, 
                static_folder='../static',
                template_folder='../templates')
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting application with {config_name} configuration")
    
    # Enable CORS
    cors_origins = app.config.get('CORS_ORIGINS', ['*'])
    logger.info(f"CORS_ORIGINS effective: {cors_origins}")
    CORS(app, origins=cors_origins)
    
    # Initialize SocketIO with Vercel-compatible configuration
    socketio = SocketIO(
        app,
        cors_allowed_origins=cors_origins,
        logger=False,  # Reduce SocketIO logging noise
        engineio_logger=False,
        # Vercel serverless compatibility settings
        ping_timeout=20,
        ping_interval=10,
        async_mode='threading'  # Use threading for better serverless compatibility
    )
    
    # Register blueprints
    register_blueprints(app)
    
    # Register test endpoints for debugging
    if app.config.get('FLASK_ENV') == 'production':
        from .socketio_test import register_test_blueprint, register_socketio_test_handlers
        register_test_blueprint(app)
        register_socketio_test_handlers(socketio)
    
    # Global error handler: log full stack traces to help diagnose 500s in serverless logs
    @app.errorhandler(Exception)
    def handle_exception(e):
        logging.exception("Unhandled exception")
        from flask import jsonify
        try:
            from werkzeug.exceptions import HTTPException
            if isinstance(e, HTTPException):
                code = int(e.code or 500)
                return jsonify(error=e.description, status=code), code
        except Exception:
            pass
        return jsonify(error=str(e)), 500

    # Register WebSocket handlers
    register_websocket_handlers(socketio)
    
    # Apply serverless patches for production
    if app.config.get('FLASK_ENV') == 'production':
        from .serverless_patch import patch_socketio_for_serverless
        socketio = patch_socketio_for_serverless(app, socketio)
    
    # Store socketio instance for access in other modules
    app.socketio = socketio  # type: ignore[attr-defined]
    
    return app, socketio
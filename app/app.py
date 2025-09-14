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
    
    # Enable CORS for development (simple approach like original)
    CORS(app)

    # Initialize SocketIO (simple approach like original)
    # Minimal Socket.IO config for Tailscale VPN (prevents packet overflow)
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*",
        # Aggressive VPN optimizations
        ping_timeout=180,           # Very long timeout for VPN
        ping_interval=60,           # Infrequent pings
        max_http_buffer_size=500000,  # Smaller buffer to prevent overflow
        # Force polling transport (more reliable over VPN)
        transports=['polling'],     # Polling only - more stable over VPN
        # Minimal logging
        engineio_logger=False,
        logger=False
    )

    logger.info("Applied simple CORS configuration for development")
    
    # Register blueprints
    register_blueprints(app)
    
    # Register test endpoints for debugging (available in both dev and production)
    try:
        from .socketio_test import register_test_blueprint, register_socketio_test_handlers
        register_test_blueprint(app)
        register_socketio_test_handlers(socketio)
    except ImportError:
        logger.warning("SocketIO test endpoints not available")
    
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

    # Register WebSocket handlers (simplified for development)
    if app.config.get('FLASK_ENV') == 'development':
        # Simple development handlers
        @socketio.on('connect')
        def handle_dev_connect():
            logger.info("Development: Client connected to SocketIO")

        @socketio.on('disconnect')
        def handle_dev_disconnect():
            logger.info("Development: Client disconnected from SocketIO")
    else:
        # Full production handlers
        register_websocket_handlers(socketio)
    
    # Apply serverless patches for production only
    if app.config.get('FLASK_ENV') == 'production':
        try:
            from .serverless_patch import patch_socketio_for_serverless
            socketio = patch_socketio_for_serverless(app, socketio)
        except ImportError:
            logger.warning("Serverless patches not available")
    
    # Store socketio instance for access in other modules
    app.socketio = socketio  # type: ignore[attr-defined]

    # Simple approach - no complex CORS overrides needed
    
    return app, socketio
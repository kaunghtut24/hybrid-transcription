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
    
    # Initialize SocketIO with transport configuration
    socketio = SocketIO(
        app,
        cors_allowed_origins=cors_origins,
        logger=False,  # Reduce SocketIO logging noise
        engineio_logger=False
    )
    
    # Register blueprints
    register_blueprints(app)
    
    # Register WebSocket handlers
    register_websocket_handlers(socketio)
    
    # Store socketio instance for access in other modules
    app.socketio = socketio  # type: ignore[attr-defined]
    
    return app, socketio
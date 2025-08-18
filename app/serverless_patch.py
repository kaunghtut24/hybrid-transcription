"""
Serverless-compatible Socket.IO configuration patch
"""

import logging
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

def patch_socketio_for_serverless(app, socketio):
    """Apply serverless-specific patches to Socket.IO configuration"""
    
    # Override Socket.IO settings for better serverless compatibility
    socketio.server_options = {
        'transports': ['polling', 'websocket'],  # Prefer polling
        'ping_timeout': 20,
        'ping_interval': 10,
        'max_http_buffer_size': 10**6,  # 1MB limit
        'cors_allowed_origins': app.config.get('CORS_ORIGINS', ['*']),
        'logger': False,
        'engineio_logger': False
    }
    
    # Add serverless-specific event handlers
    @socketio.on('connect')
    def handle_serverless_connect():
        logger.info("Serverless Socket.IO connection established")
        
    @socketio.on('disconnect')
    def handle_serverless_disconnect():
        logger.info("Serverless Socket.IO connection closed")
    
    logger.info("Applied serverless Socket.IO patches")
    return socketio

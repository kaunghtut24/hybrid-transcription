"""
Serverless-compatible Socket.IO configuration patch
"""

import logging
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

def patch_socketio_for_serverless(app, socketio):
    """Apply serverless-specific patches to Socket.IO configuration"""
    
    # Force serverless-compatible Engine.IO settings
    if hasattr(socketio.server, 'eio'):
        # Configure Engine.IO server for serverless
        eio_server = socketio.server.eio
        
        # Force polling transport only
        eio_server.transports = ['polling']
        eio_server.ping_timeout = 120  # 2 minutes for serverless cold starts
        eio_server.ping_interval = 60   # 1 minute intervals
        eio_server.max_http_buffer_size = 10**7  # 10MB for large audio data
        eio_server.allow_upgrades = False  # Disable WebSocket upgrades
        eio_server.compression = False  # Disable compression for performance
        eio_server.cookie = None  # Disable cookies for stateless serverless
        
        logger.info("Applied Engine.IO serverless configuration:")
        logger.info(f"  - Transports: {eio_server.transports}")
        logger.info(f"  - Ping timeout: {eio_server.ping_timeout}s")
        logger.info(f"  - Ping interval: {eio_server.ping_interval}s")
        logger.info(f"  - Allow upgrades: {eio_server.allow_upgrades}")
        logger.info(f"  - Compression: {eio_server.compression}")
    
    # Override Socket.IO settings for better serverless compatibility
    if hasattr(socketio, 'server_options'):
        socketio.server_options.update({
            'ping_timeout': 120,
            'ping_interval': 60,
            'max_http_buffer_size': 10**7,  # 10MB limit
            'cors_allowed_origins': app.config.get('CORS_ORIGINS', ['*']),
            'logger': False,
            'engineio_logger': False
        })
    
    # Add serverless-specific event handlers
    @socketio.on('connect')
    def handle_serverless_connect():
        logger.info("Serverless Socket.IO connection established")
        
    @socketio.on('disconnect')
    def handle_serverless_disconnect():
        logger.info("Serverless Socket.IO connection closed")
    
    # Add health check endpoint for serverless monitoring
    @socketio.on('ping')
    def handle_ping():
        logger.debug("Socket.IO ping received")
        return 'pong'
    
    logger.info("Applied comprehensive serverless Socket.IO patches")
    return socketio

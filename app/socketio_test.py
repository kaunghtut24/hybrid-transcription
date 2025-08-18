"""
Socket.IO test endpoints for debugging Vercel connectivity
"""

from flask import Blueprint, jsonify
from flask_socketio import emit
import logging

logger = logging.getLogger(__name__)

# Create test blueprint
socketio_test = Blueprint('socketio_test', __name__, url_prefix='/test')

@socketio_test.route('/socketio')
def test_socketio():
    """Test endpoint to check Socket.IO server status"""
    return jsonify({
        'status': 'Socket.IO server running',
        'message': 'Socket.IO endpoints should be available',
        'endpoints': [
            '/socket.io/',
            '/socket.io/connect',
            '/socket.io/disconnect'
        ]
    })

def register_socketio_test_handlers(socketio):
    """Register test handlers for Socket.IO debugging"""
    
    @socketio.on('test_connection')
    def handle_test_connection(data):
        """Test Socket.IO connection"""
        logger.info(f"Test connection received: {data}")
        emit('test_response', {
            'status': 'success',
            'message': 'Socket.IO is working',
            'received_data': data,
            'server_type': 'vercel_serverless'
        })
        
    @socketio.on('ping')
    def handle_ping():
        """Simple ping/pong test"""
        emit('pong', {'timestamp': 'now'})
        
    logger.info("Socket.IO test handlers registered")

def register_test_blueprint(app):
    """Register the test blueprint"""
    app.register_blueprint(socketio_test)
    logger.info("Socket.IO test blueprint registered")

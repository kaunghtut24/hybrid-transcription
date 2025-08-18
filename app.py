#!/usr/bin/env python3
"""
Flask Web Server for AI Meeting Transcription Assistant
Entry point that uses the refactored modular application structure
Optimized for cloud deployment platforms
"""

import os
import logging

# Load environment variables (optional for production environments)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available in production environments like Vercel
    # Environment variables are handled by the platform
    pass

from app import create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the refactored app
app, socketio = create_app()

# Import storage for backward compatibility with any remaining legacy code
from app.storage import storage

# Expose storage objects for backward compatibility
user_sessions = storage.user_sessions
api_keys_storage = storage.api_keys_storage
active_assemblyai_connections = storage.active_assemblyai_connections
session_data_storage = storage.session_data_storage

# Expose functions for backward compatibility
create_extended_session_data = storage.create_extended_session_data
update_session_data = storage.update_session_data
add_language_detection_event_to_session = storage.add_language_detection_event_to_session
add_transcript_to_session = storage.add_transcript_to_session
get_session_export_data = storage.get_session_export_data

# For Vercel and other serverless platforms
def handler(request):
    """Serverless function handler"""
    return app(request.environ, lambda *args: None)

if __name__ == '__main__':
    # Run the application (for local development)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting Flask application on {host}:{port}")
    logger.info(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    # Use socketio.run for WebSocket support
    socketio.run(app, host=host, port=port, debug=debug)
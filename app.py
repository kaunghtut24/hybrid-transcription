#!/usr/bin/env python3
"""
Flask Web Server for AI Meeting Transcription Assistant
Provides secure API key management and serves the frontend application
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import requests
from functools import wraps
import jwt
import hashlib
import secrets
from dotenv import load_dotenv
from assemblyai_websocket import AssemblyAIWebSocketHandler

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')

# Enable CORS for development
CORS(app)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['JWT_EXPIRATION_HOURS'] = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))

# In-memory storage for demo (use database in production)
user_sessions = {}
api_keys_storage = {}
active_assemblyai_connections = {}  # Track active AssemblyAI connections

def generate_session_token(user_id):
    """Generate a JWT session token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=app.config['JWT_EXPIRATION_HOURS']),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_session_token(token):
    """Verify and decode JWT session token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_session(f):
    """Decorator to require valid session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No authorization token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_session_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/')
def index():
    """Serve the main application"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/session', methods=['POST'])
def create_session():
    """Create a new user session"""
    # Generate a simple user ID for demo purposes
    user_id = hashlib.sha256(f"{request.remote_addr}_{datetime.utcnow()}".encode()).hexdigest()[:16]
    token = generate_session_token(user_id)
    
    user_sessions[user_id] = {
        'created_at': datetime.utcnow().isoformat(),
        'ip_address': request.remote_addr
    }
    
    # Auto-populate API keys from environment variables if available
    config = {}
    assemblyai_key = os.environ.get('ASSEMBLYAI_API_KEY')
    gemini_key = os.environ.get('GEMINI_API_KEY')
    
    if assemblyai_key:
        config['assemblyai_key'] = assemblyai_key
        logger.info(f"Auto-loaded AssemblyAI API key for user {user_id}")
    
    if gemini_key:
        config['gemini_key'] = gemini_key
        logger.info(f"Auto-loaded Gemini API key for user {user_id}")
    
    if config:
        config['last_updated'] = datetime.utcnow().isoformat()
        api_keys_storage[user_id] = config
    
    return jsonify({
        'token': token,
        'user_id': user_id,
        'expires_in': app.config['JWT_EXPIRATION_HOURS'] * 3600
    })

@app.route('/api/config', methods=['GET'])
@require_session
def get_config():
    """Get user's API configuration (without exposing keys)"""
    user_id = request.user_id
    config = api_keys_storage.get(user_id, {})
    
    # Return configuration status without exposing actual keys
    return jsonify({
        'assemblyai_configured': bool(config.get('assemblyai_key')),
        'gemini_configured': bool(config.get('gemini_key')),
        'last_updated': config.get('last_updated')
    })

@app.route('/api/config', methods=['POST'])
@require_session
def save_config():
    """Save user's API configuration"""
    user_id = request.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate API keys if provided
    assemblyai_key = data.get('assemblyai_key', '').strip()
    gemini_key = data.get('gemini_key', '').strip()
    
    config = {
        'last_updated': datetime.utcnow().isoformat()
    }
    
    if assemblyai_key:
        # Basic validation for AssemblyAI key format
        if not assemblyai_key.startswith('Bearer ') and len(assemblyai_key) > 10:
            config['assemblyai_key'] = assemblyai_key
        else:
            return jsonify({'error': 'Invalid AssemblyAI API key format'}), 400
    
    if gemini_key:
        # Basic validation for Gemini key format
        if len(gemini_key) > 10:
            config['gemini_key'] = gemini_key
        else:
            return jsonify({'error': 'Invalid Gemini API key format'}), 400
    
    api_keys_storage[user_id] = config
    
    return jsonify({
        'message': 'Configuration saved successfully',
        'assemblyai_configured': bool(config.get('assemblyai_key')),
        'gemini_configured': bool(config.get('gemini_key'))
    })

@app.route('/api/assemblyai/validate', methods=['POST'])
@require_session
def validate_assemblyai_key():
    """Validate AssemblyAI API key for Streaming v3"""
    user_id = request.user_id
    config = api_keys_storage.get(user_id, {})
    
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    try:
        # Test the API key with the new streaming client
        import assemblyai as aai
        from assemblyai.streaming.v3 import StreamingClient, StreamingClientOptions
        
        # Create client to validate the key
        client = StreamingClient(
            StreamingClientOptions(
                api_key=assemblyai_key,
                api_host="streaming.assemblyai.com",
            )
        )
        
        logger.info(f"AssemblyAI Streaming v3 key validated for user {user_id}")
        
        return jsonify({
            'valid': True,
            'api_version': 'v3',
            'api_key': assemblyai_key,  # Return the key for frontend use
            'message': 'AssemblyAI Streaming v3 API key is valid'
        })
        
    except ImportError:
        logger.error("AssemblyAI SDK not installed")
        return jsonify({'error': 'AssemblyAI SDK not installed'}), 500
    except Exception as e:
        logger.error(f"AssemblyAI key validation failed: {str(e)}")
        return jsonify({'error': 'Invalid AssemblyAI API key'}), 401

# For now, let's create a simple endpoint that tells the frontend to use Web Speech API
# In a full implementation, you'd need WebSocket support for real-time streaming
@app.route('/api/assemblyai/stream', methods=['POST'])
@require_session
def start_assemblyai_stream():
    """Start AssemblyAI streaming (placeholder for now)"""
    user_id = request.user_id
    config = api_keys_storage.get(user_id, {})
    
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    # For now, return success but recommend using Web Speech API
    # In a full implementation, this would start a WebSocket connection
    return jsonify({
        'status': 'fallback_to_webspeech',
        'message': 'AssemblyAI Streaming v3 requires WebSocket implementation. Using Web Speech API fallback.'
    })

@app.route('/api/gemini/generate', methods=['POST'])
@require_session
def gemini_generate():
    """Proxy requests to Gemini API"""
    user_id = request.user_id
    config = api_keys_storage.get(user_id, {})
    
    gemini_key = config.get('gemini_key')
    if not gemini_key:
        return jsonify({'error': 'Gemini API key not configured'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Forward request to Gemini API
        model = data.get('model', 'gemini-2.0-flash-exp')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        response = requests.post(
            url,
            params={'key': gemini_key},
            headers={'Content-Type': 'application/json'},
            json=data.get('request_body', {}),
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            logger.error(f"Gemini API request failed: {response.status_code} {response.text}")
            return jsonify({'error': 'Gemini API request failed'}), response.status_code
    
    except requests.RequestException as e:
        logger.error(f"Gemini API request error: {str(e)}")
        return jsonify({'error': 'Failed to connect to Gemini API'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

# SocketIO Event Handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    
    # Clean up any active AssemblyAI connections
    if request.sid in active_assemblyai_connections:
        handler = active_assemblyai_connections[request.sid]
        handler.stop_connection()
        del active_assemblyai_connections[request.sid]

@socketio.on('join_session')
def handle_join_session(data):
    """Handle client joining a session room"""
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)
        logger.info(f"Client {request.sid} joined session {session_id}")

@socketio.on('start_assemblyai_stream')
def handle_start_assemblyai_stream(data):
    """Start AssemblyAI streaming for a session"""
    try:
        session_token = data.get('session_token')
        session_id = data.get('session_id')
        
        if not session_token or not session_id:
            emit('assemblyai_error', {'error': 'Missing session token or session ID'})
            return
        
        # Verify session token
        user_id = verify_session_token(session_token)
        if not user_id:
            emit('assemblyai_error', {'error': 'Invalid session token'})
            return
        
        # Get API key
        config = api_keys_storage.get(user_id, {})
        assemblyai_key = config.get('assemblyai_key')
        
        if not assemblyai_key:
            emit('assemblyai_error', {'error': 'AssemblyAI API key not configured'})
            return
        
        # Create and start AssemblyAI WebSocket handler
        handler = AssemblyAIWebSocketHandler(assemblyai_key, socketio, session_id)
        
        if handler.start_connection():
            active_assemblyai_connections[request.sid] = handler
            join_room(session_id)
            emit('assemblyai_stream_started', {'status': 'started'})
            logger.info(f"AssemblyAI stream started for session {session_id}")
        else:
            emit('assemblyai_error', {'error': 'Failed to start AssemblyAI connection'})
            
    except Exception as e:
        logger.error(f"Error starting AssemblyAI stream: {e}")
        emit('assemblyai_error', {'error': str(e)})

@socketio.on('send_audio_data')
def handle_audio_data(data):
    """Handle audio data from client"""
    try:
        if request.sid in active_assemblyai_connections:
            handler = active_assemblyai_connections[request.sid]
            audio_data = data.get('audio_data')
            
            if audio_data:
                # Convert base64 audio data back to bytes if needed
                import base64
                if isinstance(audio_data, str):
                    audio_bytes = base64.b64decode(audio_data)
                else:
                    audio_bytes = audio_data
                
                handler.send_audio_data(audio_bytes)
                
    except Exception as e:
        logger.error(f"Error handling audio data: {e}")
        emit('assemblyai_error', {'error': str(e)})

@socketio.on('stop_assemblyai_stream')
def handle_stop_assemblyai_stream():
    """Stop AssemblyAI streaming"""
    try:
        if request.sid in active_assemblyai_connections:
            handler = active_assemblyai_connections[request.sid]
            handler.stop_connection()
            del active_assemblyai_connections[request.sid]
            emit('assemblyai_stream_stopped', {'status': 'stopped'})
            logger.info(f"AssemblyAI stream stopped for client {request.sid}")
            
    except Exception as e:
        logger.error(f"Error stopping AssemblyAI stream: {e}")
        emit('assemblyai_error', {'error': str(e)})

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask-SocketIO server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)

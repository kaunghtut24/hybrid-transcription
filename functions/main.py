"""
Firebase Cloud Functions for AI Meeting Transcription Assistant
Provides secure API key management and proxy services
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from firebase_functions import https_fn, options
import requests
import jwt
import hashlib
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))

# In-memory storage for demo (use Firestore in production)
user_sessions = {}
api_keys_storage = {}

def generate_session_token(user_id):
    """Generate a JWT session token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_session_token(token):
    """Verify and decode JWT session token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_session(f):
    """Decorator to require valid session"""
    def decorated_function(req):
        auth_header = req.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization token provided'}), 401
        
        token = auth_header
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_session_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        req.user_id = user_id
        return f(req)
    
    return decorated_function

@https_fn.on_request(
    cors=options.CorsOptions(
        cors_origins=["*"],
        cors_methods=["GET", "POST", "OPTIONS"],
        cors_allow_headers=["Content-Type", "Authorization"]
    )
)
def api(req):
    """Main API endpoint router"""
    
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        return '', 200
    
    path = req.path.replace('/api', '')
    
    if path == '/session' and req.method == 'POST':
        return create_session(req)
    elif path == '/config' and req.method == 'GET':
        return get_config(req)
    elif path == '/config' and req.method == 'POST':
        return save_config(req)
    elif path == '/assemblyai/token' and req.method == 'POST':
        return get_assemblyai_token(req)
    elif path == '/gemini/generate' and req.method == 'POST':
        return gemini_generate(req)
    elif path == '/health':
        return health_check(req)
    else:
        return jsonify({'error': 'Not found'}), 404

def create_session(req):
    """Create a new user session"""
    # Generate a simple user ID for demo purposes
    user_id = hashlib.sha256(f"{req.remote_addr}_{datetime.utcnow()}".encode()).hexdigest()[:16]
    token = generate_session_token(user_id)
    
    user_sessions[user_id] = {
        'created_at': datetime.utcnow().isoformat(),
        'ip_address': req.remote_addr
    }
    
    return jsonify({
        'token': token,
        'user_id': user_id,
        'expires_in': JWT_EXPIRATION_HOURS * 3600
    })

@require_session
def get_config(req):
    """Get user's API configuration (without exposing keys)"""
    user_id = req.user_id
    config = api_keys_storage.get(user_id, {})
    
    return jsonify({
        'assemblyai_configured': bool(config.get('assemblyai_key')),
        'gemini_configured': bool(config.get('gemini_key')),
        'last_updated': config.get('last_updated')
    })

@require_session
def save_config(req):
    """Save user's API configuration"""
    user_id = req.user_id
    data = req.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    assemblyai_key = data.get('assemblyai_key', '').strip()
    gemini_key = data.get('gemini_key', '').strip()
    
    config = {
        'last_updated': datetime.utcnow().isoformat()
    }
    
    if assemblyai_key:
        if len(assemblyai_key) > 10:
            config['assemblyai_key'] = assemblyai_key
        else:
            return jsonify({'error': 'Invalid AssemblyAI API key format'}), 400
    
    if gemini_key:
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

@require_session
def get_assemblyai_token(req):
    """Get temporary token for AssemblyAI WebSocket connection"""
    user_id = req.user_id
    config = api_keys_storage.get(user_id, {})
    
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    try:
        response = requests.post(
            'https://api.assemblyai.com/v2/realtime/token',
            headers={
                'Authorization': assemblyai_key,
                'Content-Type': 'application/json'
            },
            json={'expires_in': 3600},
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            logger.error(f"AssemblyAI token request failed: {response.status_code}")
            return jsonify({'error': 'Failed to get AssemblyAI token'}), response.status_code
    
    except requests.RequestException as e:
        logger.error(f"AssemblyAI token request error: {str(e)}")
        return jsonify({'error': 'Failed to connect to AssemblyAI'}), 500

@require_session
def gemini_generate(req):
    """Proxy requests to Gemini API"""
    user_id = req.user_id
    config = api_keys_storage.get(user_id, {})
    
    gemini_key = config.get('gemini_key')
    if not gemini_key:
        return jsonify({'error': 'Gemini API key not configured'}), 400
    
    data = req.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
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
            logger.error(f"Gemini API request failed: {response.status_code}")
            return jsonify({'error': 'Gemini API request failed'}), response.status_code
    
    except requests.RequestException as e:
        logger.error(f"Gemini API request error: {str(e)}")
        return jsonify({'error': 'Failed to connect to Gemini API'}), 500

def health_check(req):
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

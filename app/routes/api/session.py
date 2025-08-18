"""
Session management API routes
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app.auth import create_user_session, require_session
from app.storage import storage
import logging

logger = logging.getLogger(__name__)
session_api = Blueprint('session_api', __name__)

@session_api.route('', methods=['POST'])
def create_session():
    """Create a new user session"""
    user_id, token, session_data = create_user_session(request.remote_addr)
    
    storage.user_sessions[user_id] = session_data
    
    # Auto-populate API keys from environment variables if available
    from flask import current_app
    config = storage.api_keys_storage.get(user_id, {})
    
    # Load from environment variables if not already configured
    assemblyai_key = current_app.config.get('ASSEMBLYAI_API_KEY')
    gemini_key = current_app.config.get('GEMINI_API_KEY')
    
    # Only auto-load if user doesn't have keys configured
    if assemblyai_key and not config.get('assemblyai_key'):
        config['assemblyai_key'] = assemblyai_key
        config['auto_loaded_assemblyai'] = True
        logger.info(f"Auto-loaded AssemblyAI API key from environment for user {user_id}")
    
    if gemini_key and not config.get('gemini_key'):
        config['gemini_key'] = gemini_key
        config['auto_loaded_gemini'] = True
        logger.info(f"Auto-loaded Gemini API key from environment for user {user_id}")
    
    if config:
        config['last_updated'] = datetime.utcnow().isoformat()
        storage.api_keys_storage[user_id] = config
    
    return jsonify({
        'token': token,
        'user_id': user_id,
        'expires_in': current_app.config['JWT_EXPIRATION_HOURS'] * 3600
    })

@session_api.route('/status', methods=['GET'])
@require_session
def session_status():
    """Get session status (JSON API)"""
    user_id = request.user_id
    session_data = storage.user_sessions.get(user_id, {})
    
    return jsonify({
        'status': 'active',
        'user_id': user_id,
        'created_at': session_data.get('created_at'),
        'server_time': datetime.utcnow().isoformat()
    })

@session_api.route('/status-html', methods=['GET'])
def session_status_form():
    """Get session status (HTML form compatible)"""
    try:
        return f"""
        <html>
        <head><title>Session Status</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>📊 Session Status</h2>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <p><strong>Status:</strong> Active</p>
                <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Server:</strong> Running</p>
            </div>
            <p><a href="/" style="color: #007bff;">← Back to Main App</a></p>
        </body>
        </html>
        """, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"""
        <html>
        <head><title>Status Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>❌ Status Check Failed</h2>
            <p>Error: {str(e)}</p>
            <p><a href="/" style="color: #007bff;">← Back to Main App</a></p>
        </body>
        </html>
        """, 500, {'Content-Type': 'text/html'}
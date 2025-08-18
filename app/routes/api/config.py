"""
Configuration management API routes
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app.auth import require_session
from app.storage import storage
import logging
import os

logger = logging.getLogger(__name__)
config_api = Blueprint('config_api', __name__)

@config_api.route('/initial', methods=['GET'])
def get_initial_config():
    """Get initial configuration including environment API keys (no session required)"""
    # Check environment variables for API keys
    assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    
    return jsonify({
        'assemblyai_available': bool(assemblyai_key),
        'gemini_available': bool(gemini_key),
        'assemblyai_key': assemblyai_key if assemblyai_key else None,
        'gemini_key': gemini_key if gemini_key else None,
        'environment_loaded': True
    })

@config_api.route('', methods=['GET'])
@require_session
def get_config():
    """Get user's API configuration (without exposing keys)"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Also check environment variables as fallback
    env_assemblyai = os.getenv('ASSEMBLYAI_API_KEY')
    env_gemini = os.getenv('GEMINI_API_KEY')
    
    # Auto-load environment keys if user doesn't have their own
    if env_assemblyai and not config.get('assemblyai_key'):
        config['assemblyai_key'] = env_assemblyai
        config['auto_loaded_assemblyai'] = True
        storage.api_keys_storage[user_id] = config
    
    if env_gemini and not config.get('gemini_key'):
        config['gemini_key'] = env_gemini
        config['auto_loaded_gemini'] = True
        storage.api_keys_storage[user_id] = config
    
    # Get model configuration
    model_config = config.get('assemblyai_model_config', {})
    
    # Return configuration status without exposing actual keys
    return jsonify({
        'assemblyai_configured': bool(config.get('assemblyai_key')),
        'gemini_configured': bool(config.get('gemini_key')),
        'assemblyai_from_env': bool(config.get('auto_loaded_assemblyai')),
        'gemini_from_env': bool(config.get('auto_loaded_gemini')),
        'last_updated': config.get('last_updated'),
        'model_preferences': {
            'selected_model': model_config.get('selected_model', 'universal_streaming'),
            'streaming_model': model_config.get('streaming_model', 'universal_streaming'),
            'file_upload_model': model_config.get('file_upload_model', 'universal'),
            'last_updated': model_config.get('last_updated')
        }
    })

@config_api.route('', methods=['POST'])
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
    
    # Get existing config or create new one
    config = storage.api_keys_storage.get(user_id, {})
    config['last_updated'] = datetime.utcnow().isoformat()
    
    if assemblyai_key:
        # Basic validation for AssemblyAI key format
        if len(assemblyai_key) >= 32 and assemblyai_key.replace('-', '').replace('_', '').isalnum():
            config['assemblyai_key'] = assemblyai_key
        else:
            return jsonify({'error': 'Invalid AssemblyAI API key format. Key should be at least 32 characters long.'}), 400
    
    if gemini_key:
        # Basic validation for Gemini key format
        if len(gemini_key) >= 20:
            config['gemini_key'] = gemini_key
        else:
            return jsonify({'error': 'Invalid Gemini API key format. Key should be at least 20 characters long.'}), 400
    
    # Only update if we have valid keys to save
    if assemblyai_key or gemini_key or 'assemblyai_key' in config or 'gemini_key' in config:
        storage.api_keys_storage[user_id] = config
    else:
        return jsonify({'error': 'No valid API keys provided'}), 400
    
    return jsonify({
        'message': 'Configuration saved successfully',
        'assemblyai_configured': bool(config.get('assemblyai_key')),
        'gemini_configured': bool(config.get('gemini_key'))
    })
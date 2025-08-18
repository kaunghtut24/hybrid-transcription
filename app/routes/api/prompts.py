"""
Custom prompt management API routes
"""

from flask import Blueprint, request, jsonify
from app.auth import require_session
from app.storage import storage
import logging

logger = logging.getLogger(__name__)
prompts_api = Blueprint('prompts_api', __name__)

@prompts_api.route('', methods=['GET'])
@require_session
def get_user_prompts():
    """Get all user's custom prompts"""
    user_id = request.user_id
    
    try:
        from services.prompt_manager import CustomPromptManager
        prompt_manager = CustomPromptManager(storage_backend=storage.api_keys_storage)
        
        user_prompts = prompt_manager.get_user_prompts(user_id)
        prompt_status = prompt_manager.get_user_prompt_status(user_id)
        
        return jsonify({
            'prompts': user_prompts,
            'status': prompt_status,
            'available_types': ['summarization', 'translation']
        })
        
    except Exception as e:
        logger.error(f"Error getting user prompts: {e}")
        return jsonify({'error': str(e)}), 500

@prompts_api.route('/<prompt_type>', methods=['GET'])
@require_session
def get_prompt(prompt_type):
    """Get a specific prompt by type"""
    user_id = request.user_id
    
    if prompt_type not in ['summarization', 'translation']:
        return jsonify({'error': 'Invalid prompt type'}), 400
    
    try:
        from services.prompt_manager import CustomPromptManager
        prompt_manager = CustomPromptManager(storage_backend=storage.api_keys_storage)
        
        prompt_data = prompt_manager.get_prompt(user_id, prompt_type)
        
        return jsonify({
            'prompt_type': prompt_type,
            'prompt_data': prompt_data
        })
        
    except Exception as e:
        logger.error(f"Error getting prompt {prompt_type}: {e}")
        return jsonify({'error': str(e)}), 500

@prompts_api.route('/<prompt_type>', methods=['POST'])
@require_session
def save_custom_prompt(prompt_type):
    """Save or update a custom prompt"""
    user_id = request.user_id
    
    if prompt_type not in ['summarization', 'translation']:
        return jsonify({'error': 'Invalid prompt type'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        from services.prompt_manager import CustomPromptManager
        prompt_manager = CustomPromptManager(storage_backend=storage.api_keys_storage)
        
        result = prompt_manager.save_custom_prompt(user_id, prompt_type, data)
        
        return jsonify({
            'message': f'Custom {prompt_type} prompt saved successfully',
            'prompt_type': prompt_type,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error saving custom prompt: {e}")
        return jsonify({'error': str(e)}), 500

@prompts_api.route('/defaults', methods=['GET'])
def get_default_prompts():
    """Get all default prompts (no authentication required)"""
    try:
        from services.prompt_manager import CustomPromptManager
        prompt_manager = CustomPromptManager(storage_backend=storage.api_keys_storage)
        
        defaults = prompt_manager.get_default_prompts()
        
        return jsonify({
            'default_prompts': defaults
        })
        
    except Exception as e:
        logger.error(f"Error getting default prompts: {e}")
        return jsonify({'error': str(e)}), 500
"""
Gemini AI API integration routes
"""

from flask import Blueprint, request, jsonify
from app.auth import require_session
from app.storage import storage
import requests
import logging

logger = logging.getLogger(__name__)
gemini_api = Blueprint('gemini_api', __name__)

@gemini_api.route('/generate', methods=['POST'])
@require_session
def gemini_generate():
    """Proxy requests to Gemini API with custom prompt support"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Try user config first, then environment variable
    gemini_key = config.get('gemini_key')
    if not gemini_key:
        import os
        gemini_key = os.getenv('GEMINI_API_KEY')
    
    if not gemini_key:
        return jsonify({'error': 'Gemini API key not configured'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Check if this is a request that should use custom prompts
        use_custom_prompt = data.get('use_custom_prompt', False)
        prompt_type = data.get('prompt_type')
        template_vars = data.get('template_vars', {})
        
        request_body = data.get('request_body', {})
        
        # If custom prompt is requested, apply it
        if use_custom_prompt and prompt_type:
            try:
                from services.prompt_manager import CustomPromptManager
                prompt_manager = CustomPromptManager(storage_backend=storage.api_keys_storage)
                
                formatted_prompt = prompt_manager.apply_prompt_template(
                    user_id, prompt_type, **template_vars
                )
                
                # Update the request body with the formatted prompt
                if 'contents' in request_body and len(request_body['contents']) > 0:
                    if 'parts' in request_body['contents'][0]:
                        request_body['contents'][0]['parts'][0]['text'] = formatted_prompt
                    else:
                        request_body['contents'][0]['parts'] = [{'text': formatted_prompt}]
                else:
                    request_body['contents'] = [{
                        'parts': [{'text': formatted_prompt}]
                    }]
                
                logger.info(f"Applied custom {prompt_type} prompt for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error applying custom prompt: {e}")
                return jsonify({'error': f'Failed to apply custom prompt: {str(e)}'}), 400
        
        # Forward request to Gemini API
        model = data.get('model', 'gemini-2.0-flash-exp')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        response = requests.post(
            url,
            params={'key': gemini_key},
            headers={'Content-Type': 'application/json'},
            json=request_body,
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

@gemini_api.route('/summarize', methods=['POST'])
@require_session
def gemini_summarize_with_custom_prompt():
    """Generate meeting summary using custom or default prompt"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Try user config first, then environment variable
    gemini_key = config.get('gemini_key')
    if not gemini_key:
        import os
        gemini_key = os.getenv('GEMINI_API_KEY')
    
    if not gemini_key:
        return jsonify({'error': 'Gemini API key not configured'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    transcript = data.get('transcript', '').strip()
    if not transcript:
        return jsonify({'error': 'Transcript is required'}), 400
    
    try:
        from services.prompt_manager import CustomPromptManager
        prompt_manager = CustomPromptManager(storage_backend=storage.api_keys_storage)
        
        # Get the appropriate prompt (custom or default)
        formatted_prompt = prompt_manager.apply_prompt_template(
            user_id, 'summarization', transcript=transcript
        )
        
        # Prepare Gemini API request
        model = data.get('model', 'gemini-2.0-flash-exp')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        request_body = {
            'contents': [{
                'parts': [{'text': formatted_prompt}]
            }],
            'generationConfig': {
                'temperature': 0.7,
                'topK': 40,
                'topP': 0.95,
                'maxOutputTokens': 2048
            }
        }
        
        response = requests.post(
            url,
            params={'key': gemini_key},
            headers={'Content-Type': 'application/json'},
            json=request_body,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract the generated text
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    summary = candidate['content']['parts'][0].get('text', '')
                    
                    return jsonify({
                        'summary': summary,
                        'used_custom_prompt': not prompt_manager.get_user_prompt_status(user_id).get('summarization', {}).get('is_default', True),
                        'status': 'success'
                    })
            
            return jsonify({'error': 'No summary generated'}), 500
        else:
            logger.error(f"Gemini summarization failed: {response.status_code} {response.text}")
            return jsonify({'error': 'Failed to generate summary'}), response.status_code
    
    except Exception as e:
        logger.error(f"Summarization error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@gemini_api.route('/translate', methods=['POST'])
@require_session
def gemini_translate():
    """Translate text using Gemini AI"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Try user config first, then environment variable
    gemini_key = config.get('gemini_key')
    if not gemini_key:
        import os
        gemini_key = os.getenv('GEMINI_API_KEY')
    
    if not gemini_key:
        return jsonify({'error': 'Gemini API key not configured'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    text = data.get('text', '').strip()
    target_language = data.get('target_language', 'es')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        # Language mapping for better prompts
        language_names = {
            'es': 'Spanish', 'fr': 'French', 'de': 'German', 'it': 'Italian',
            'pt': 'Portuguese', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese (Simplified)',
            'ar': 'Arabic', 'ru': 'Russian', 'my': 'Myanmar (Burmese)', 'hi': 'Hindi', 'bn': 'Bengali'
        }
        
        target_lang_name = language_names.get(target_language, target_language)
        
        # Create translation prompt
        prompt = f"""Please translate the following text to {target_lang_name}. 
        Maintain the original meaning and context. If it's a meeting transcript, preserve the conversational tone.
        
        Text to translate:
        {text}
        
        Translation:"""
        
        # Prepare Gemini API request
        model = data.get('model', 'gemini-2.0-flash-exp')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        request_body = {
            'contents': [{
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'temperature': 0.3,  # Lower temperature for more consistent translations
                'topK': 40,
                'topP': 0.95,
                'maxOutputTokens': 2048
            }
        }
        
        response = requests.post(
            url,
            params={'key': gemini_key},
            headers={'Content-Type': 'application/json'},
            json=request_body,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract the generated text
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    translation = candidate['content']['parts'][0].get('text', '')
                    
                    return jsonify({
                        'translation': translation,
                        'target_language': target_language,
                        'target_language_name': target_lang_name,
                        'status': 'success'
                    })
            
            return jsonify({'error': 'No translation generated'}), 500
        else:
            logger.error(f"Gemini translation failed: {response.status_code} {response.text}")
            return jsonify({'error': 'Failed to generate translation'}), response.status_code
    
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@gemini_api.route('/extract', methods=['POST'])
@require_session
def gemini_extract():
    """Extract key information from text using Gemini AI"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Try user config first, then environment variable
    gemini_key = config.get('gemini_key')
    if not gemini_key:
        import os
        gemini_key = os.getenv('GEMINI_API_KEY')
    
    if not gemini_key:
        return jsonify({'error': 'Gemini API key not configured'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        # Create extraction prompt
        prompt = f"""Please analyze the following text and extract key information in a structured format. 
        Provide the following:
        
        1. **Key Topics**: Main subjects discussed
        2. **Important Names**: People, organizations, places mentioned
        3. **Action Items**: Tasks, decisions, or next steps identified
        4. **Key Dates/Times**: Important dates, deadlines, or time references
        5. **Key Numbers**: Important statistics, amounts, or metrics
        6. **Main Decisions**: Key conclusions or decisions made
        
        Format your response clearly with headers and bullet points.
        
        Text to analyze:
        {text}
        
        Analysis:"""
        
        # Prepare Gemini API request
        model = data.get('model', 'gemini-2.0-flash-exp')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        request_body = {
            'contents': [{
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'temperature': 0.3,  # Lower temperature for more structured output
                'topK': 40,
                'topP': 0.95,
                'maxOutputTokens': 2048
            }
        }
        
        response = requests.post(
            url,
            params={'key': gemini_key},
            headers={'Content-Type': 'application/json'},
            json=request_body,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract the generated text
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    extraction = candidate['content']['parts'][0].get('text', '')
                    
                    return jsonify({
                        'extraction': extraction,
                        'status': 'success'
                    })
            
            return jsonify({'error': 'No extraction generated'}), 500
        else:
            logger.error(f"Gemini extraction failed: {response.status_code} {response.text}")
            return jsonify({'error': 'Failed to generate extraction'}), response.status_code
    
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        return jsonify({'error': str(e)}), 500
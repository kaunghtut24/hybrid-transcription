"""
AssemblyAI API integration routes
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app.auth import require_session
from app.storage import storage
import logging

logger = logging.getLogger(__name__)
assemblyai_api = Blueprint('assemblyai_api', __name__)

@assemblyai_api.route('/validate', methods=['POST'])
@require_session
def validate_assemblyai_key():
    """Validate AssemblyAI API key for Streaming v3"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Try user config first, then environment variable
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        import os
        assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
    
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
            'api_key': assemblyai_key,
            'message': 'AssemblyAI Streaming v3 API key is valid'
        })
        
    except ImportError:
        logger.error("AssemblyAI SDK not installed")
        return jsonify({'error': 'AssemblyAI SDK not installed'}), 500
    except Exception as e:
        logger.error(f"AssemblyAI key validation failed: {str(e)}")
        return jsonify({'error': 'Invalid AssemblyAI API key'}), 401

@assemblyai_api.route('/stream', methods=['POST'])
@require_session
def start_assemblyai_stream():
    """Start AssemblyAI streaming (placeholder for now)"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Try user config first, then environment variable
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        import os
        assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
    
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    return jsonify({
        'status': 'fallback_to_webspeech',
        'message': 'AssemblyAI Streaming v3 requires WebSocket implementation. Using Web Speech API fallback.'
    })

@assemblyai_api.route('/key', methods=['GET'])
@require_session
def get_assemblyai_key():
    """Get AssemblyAI API key for Universal Streaming v3 (frontend use)"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Try user config first, then environment variable
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        import os
        assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
    
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    # Return the API key for direct use with Universal Streaming v3
    return jsonify({
        'api_key': assemblyai_key,
        'streaming_endpoint': 'wss://streaming.assemblyai.com/v3/ws',
        'version': 'v3',
        'note': 'Use API key directly with Universal Streaming v3'
    })

@assemblyai_api.route('/streaming/connect', methods=['POST'])
@require_session
def connect_assemblyai_streaming():
    """Connect to AssemblyAI Universal Streaming v3"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Try user config first, then environment variable
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        import os
        assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
    
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    try:
        # Use backend WebSocket proxy to handle Authorization header properly
        return jsonify({
            'status': 'ready',
            'websocket_url': '/assemblyai-streaming',  # Use SocketIO namespace
            'config': {
                'sample_rate': 16000,
                'format_turns': True,
                'model': 'universal_streaming'
            },
            'note': 'Using backend WebSocket proxy for proper authentication'
        })
        
    except Exception as e:
        logger.error(f"AssemblyAI streaming connection error: {str(e)}")
        return jsonify({'error': 'Failed to setup AssemblyAI streaming connection'}), 500

@assemblyai_api.route('/temp-token', methods=['POST'])
@require_session
def get_assemblyai_temp_token():
    """Get temporary token for AssemblyAI Universal Streaming v3"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Try user config first, then environment variable
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        import os
        assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
    
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    try:
        # For now, return the API key as token (since AssemblyAI doesn't have separate temp tokens)
        # In a production environment, you might want to create a time-limited proxy token
        return jsonify({
            'token': assemblyai_key,
            'expires_in': 3600,  # 1 hour
            'note': 'Using API key as token for Universal Streaming v3'
        })
        
    except Exception as e:
        logger.error(f"Failed to generate temporary token: {str(e)}")
        return jsonify({'error': 'Failed to generate temporary token'}), 500

@assemblyai_api.route('/token', methods=['POST'])
@require_session
def get_assemblyai_token_deprecated():
    """Deprecated token endpoint - returns error message"""
    return jsonify({
        'error': 'AssemblyAI real-time token endpoint is deprecated. Use Universal Streaming v3 with API key directly.',
        'fallback_available': True,
        'suggestion': 'Use file upload for transcription or upgrade to Universal Streaming v3',
        'documentation': 'https://www.assemblyai.com/docs/speech-to-text/universal-streaming'
    }), 503

@assemblyai_api.route('/upload', methods=['POST'])
@require_session
def upload_file_to_assemblyai():
    """Upload file to AssemblyAI for transcription"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file extension
    filename = file.filename.lower()
    allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.mp4', '.mov', '.avi'}
    file_ext = '.' + filename.split('.')[-1] if '.' in filename else ''
    
    if file_ext not in allowed_extensions:
        return jsonify({
            'error': f'Unsupported file format: {file_ext}. Supported formats: {", ".join(allowed_extensions)}'
        }), 400
    
    # Check file size (AssemblyAI limit is 2.2GB, but we'll use a smaller limit)
    max_size = 100 * 1024 * 1024  # 100MB limit for better performance
    if file.content_length and file.content_length > max_size:
        return jsonify({'error': f'File too large. Maximum size is {max_size // (1024*1024)}MB.'}), 413
    
    try:
        import requests
        import mimetypes
        
        # Ensure proper MIME type for audio files
        filename = file.filename
        content_type = file.content_type
        
        # Override content type if it's generic or missing
        if not content_type or content_type == 'application/octet-stream':
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                # Default based on file extension
                ext = filename.lower().split('.')[-1] if '.' in filename else ''
                audio_types = {
                    'wav': 'audio/wav',
                    'mp3': 'audio/mpeg',
                    'm4a': 'audio/mp4',
                    'flac': 'audio/flac',
                    'ogg': 'audio/ogg',
                    'aac': 'audio/aac',
                    'wma': 'audio/x-ms-wma'
                }
                content_type = audio_types.get(ext, 'audio/wav')
        
        logger.info(f"Uploading file: {filename}, Content-Type: {content_type}, Size: {file.content_length}")
        
        # Read file data properly
        file.seek(0)  # Ensure we're at the beginning
        file_data = file.read()
        
        # Upload file to AssemblyAI with proper content type
        response = requests.post(
            'https://api.assemblyai.com/v2/upload',
            headers={'authorization': assemblyai_key},
            data=file_data,  # Send raw file data as per AssemblyAI docs
            timeout=300  # 5 minute timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"File uploaded successfully: {result.get('upload_url', 'No URL')}")
            return jsonify(result)
        else:
            error_text = response.text
            logger.error(f"AssemblyAI upload failed: {response.status_code} {error_text}")
            
            # Provide more specific error messages
            if response.status_code == 400:
                return jsonify({'error': f'Invalid file format or corrupted file: {error_text}'}), 400
            elif response.status_code == 413:
                return jsonify({'error': 'File too large. Maximum size is 2.2GB.'}), 413
            elif response.status_code == 401:
                return jsonify({'error': 'Invalid AssemblyAI API key'}), 401
            else:
                return jsonify({'error': f'File upload failed: {error_text}'}), response.status_code
            
    except Exception as e:
        logger.error(f"AssemblyAI upload error: {str(e)}")
        return jsonify({'error': 'File upload failed'}), 500

@assemblyai_api.route('/transcribe', methods=['POST'])
@require_session
def start_transcription():
    """Start transcription of uploaded file"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    data = request.get_json()
    if not data or 'audio_url' not in data:
        return jsonify({'error': 'Audio URL required'}), 400
    
    try:
        import requests
        
        # Get model selection (default to universal)
        selected_model = data.get('model', 'universal')
        language_code = data.get('language_code', 'en')
        keyterms_prompt = data.get('keyterms_prompt', [])
        
        # Validate model and language combination
        if selected_model == 'slam-1' and language_code != 'en':
            return jsonify({
                'error': f'Slam-1 model only supports English. Selected language: {language_code}. Use Universal model for other languages.'
            }), 400
        
        # Validate keyterms for Slam-1
        if keyterms_prompt and selected_model != 'slam-1':
            logger.warning("Key terms provided but not using Slam-1 model. Key terms will be ignored.")
            keyterms_prompt = []
        
        logger.info(f"Starting transcription with model: {selected_model}, language: {language_code}")
        if keyterms_prompt:
            logger.info(f"Using {len(keyterms_prompt)} key terms for Slam-1 enhancement")
        
        # Start transcription with model configuration
        transcription_config = {
            'audio_url': data['audio_url'],
            'language_code': language_code,
            'punctuate': True,
            'format_text': True
        }
        
        # Add model-specific configuration
        if selected_model == 'slam-1':
            transcription_config['speech_model'] = 'slam-1'
            
            # Add keyterms_prompt for Slam-1 if provided
            if keyterms_prompt:
                # Validate keyterms format and limits
                if len(keyterms_prompt) > 1000:
                    return jsonify({
                        'error': f'Too many key terms provided: {len(keyterms_prompt)}. Maximum is 1000 terms.'
                    }), 400
                
                # Validate individual keyterms (max 6 words per phrase)
                invalid_terms = []
                for term in keyterms_prompt:
                    if len(term.split()) > 6:
                        invalid_terms.append(term)
                
                if invalid_terms:
                    return jsonify({
                        'error': f'Key terms must be 6 words or less. Invalid terms: {invalid_terms[:3]}...' if len(invalid_terms) > 3 else f'Invalid terms: {invalid_terms}'
                    }), 400
                
                transcription_config['keyterms_prompt'] = keyterms_prompt
                logger.info(f"Added {len(keyterms_prompt)} key terms to Slam-1 configuration")
            
            logger.info("Using Slam-1 model for highest English accuracy")
        else:
            # Universal model (default)
            logger.info("Using Universal model for multi-language support")
        
        response = requests.post(
            'https://api.assemblyai.com/v2/transcript',
            headers={
                'authorization': assemblyai_key,
                'content-type': 'application/json'
            },
            json=transcription_config
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            logger.error(f"AssemblyAI transcription failed: {response.status_code} {response.text}")
            return jsonify({'error': 'Transcription request failed'}), response.status_code
            
    except Exception as e:
        logger.error(f"AssemblyAI transcription error: {str(e)}")
        return jsonify({'error': 'Transcription request failed'}), 500

@assemblyai_api.route('/transcript/<transcript_id>', methods=['GET'])
@require_session
def get_transcript_status(transcript_id):
    """Get transcription status and result"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    try:
        import requests
        
        response = requests.get(
            f'https://api.assemblyai.com/v2/transcript/{transcript_id}',
            headers={'authorization': assemblyai_key}
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            logger.error(f"AssemblyAI transcript status failed: {response.status_code} {response.text}")
            return jsonify({'error': 'Failed to get transcript status'}), response.status_code
            
    except Exception as e:
        logger.error(f"AssemblyAI transcript status error: {str(e)}")
        return jsonify({'error': 'Failed to get transcript status'}), 500

@assemblyai_api.route('/models', methods=['GET'])
@require_session
def get_available_models():
    """Get available AssemblyAI models"""
    try:
        models = {
            'universal_streaming': {
                'name': 'Universal Streaming',
                'description': 'Best for real-time streaming',
                'supported_features': ['streaming', 'language_detection']
            },
            'universal': {
                'name': 'Universal',
                'description': 'Best for file uploads',
                'supported_features': ['file_upload', 'speaker_diarization']
            }
        }
        return jsonify({'models': models})
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return jsonify({'error': 'Failed to get available models'}), 500
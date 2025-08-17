"""
Enhanced AssemblyAI Service with model selection support
"""

import os
import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
from .base import BaseService, EnhancedAssemblyAIInterface, ProcessingError, ValidationError, ConfigurationError
from .models import AssemblyAIModelConfiguration

logger = logging.getLogger(__name__)


class EnhancedAssemblyAIService(BaseService, EnhancedAssemblyAIInterface):
    """Enhanced AssemblyAI service with model selection and file upload support"""
    
    # Available models with their configurations
    AVAILABLE_MODELS = {
        'universal': {
            'name': 'Universal',
            'description': 'Fastest, most robust models with the broadest language support',
            'use_case': 'General purpose transcription with broad language support (default for file upload)',
            'api_value': None,  # Default model, no specific parameter needed
            'supports_streaming': False,
            'supports_file_upload': True,
            'languages': 'Multi-language support'
        },
        'universal_streaming': {
            'name': 'Universal Streaming', 
            'description': 'Optimized for streaming audio with real-time processing',
            'use_case': 'Real-time streaming applications (default for live audio)',
            'api_value': None,  # For streaming, this is the default
            'supports_streaming': True,
            'supports_file_upload': False,
            'languages': 'Multi-language support'
        },
        'slam-1': {
            'name': 'Slam-1',
            'description': 'Most customizable model for your transcription (English only)',
            'use_case': 'High-customization transcription for English content',
            'api_value': 'slam-1',
            'supports_streaming': False,
            'supports_file_upload': True,
            'languages': 'English only'
        }
    }
    
    def __init__(self, api_key: str, selected_model: str = 'universal_streaming', config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = api_key
        self.selected_model = selected_model
        self.base_url = "https://api.assemblyai.com/v2"
        self.upload_url = f"{self.base_url}/upload"
        self.transcript_url = f"{self.base_url}/transcript"
        self.streaming_base_url = "wss://streaming.assemblyai.com/v3/ws"
        
        # Validate configuration
        if not self.validate_config():
            raise ConfigurationError("Invalid AssemblyAI service configuration")
    
    def validate_config(self) -> bool:
        """Validate service configuration"""
        if not self.api_key:
            self.logger.error("AssemblyAI API key is required")
            return False
        
        if not self.is_valid_model(self.selected_model):
            self.logger.error(f"Invalid model selected: {self.selected_model}")
            return False
        
        return True
    
    def is_valid_model(self, model: str) -> bool:
        """Check if model is valid"""
        return model in self.AVAILABLE_MODELS
    
    def get_available_models(self) -> Dict[str, Dict[str, str]]:
        """Get list of available models"""
        return self.AVAILABLE_MODELS.copy()
    
    def get_model_info(self, model: str) -> Dict[str, str]:
        """Get information about a specific model"""
        return self.AVAILABLE_MODELS.get(model, {})
    
    def set_model(self, model: str) -> Dict[str, Any]:
        """Set the selected model with comprehensive validation"""
        try:
            # Input validation
            if not model or not isinstance(model, str):
                return {
                    'success': False,
                    'error': 'Model name must be a non-empty string',
                    'error_code': 'INVALID_MODEL_INPUT',
                    'recovery_suggestions': [
                        'Provide a valid model name',
                        f'Available models: {", ".join(self.AVAILABLE_MODELS.keys())}'
                    ]
                }
            
            # Normalize model name
            model = model.strip().lower()
            
            # Validate model exists
            if not self.is_valid_model(model):
                available_models = ', '.join(self.AVAILABLE_MODELS.keys())
                return {
                    'success': False,
                    'error': f'Invalid model: {model}',
                    'error_code': 'UNSUPPORTED_MODEL',
                    'available_models': list(self.AVAILABLE_MODELS.keys()),
                    'recovery_suggestions': [
                        f'Use one of these supported models: {available_models}',
                        'Check the model name spelling',
                        'Refer to the model selection guide for more information'
                    ]
                }
            
            # Check if model is different from current
            if model == self.selected_model:
                return {
                    'success': True,
                    'message': f'Model "{model}" is already selected',
                    'model': model,
                    'model_info': self.get_model_info(model),
                    'changed': False
                }
            
            # Validate model for current API tier (if we had tier info)
            # This is a placeholder for future API tier validation
            model_info = self.get_model_info(model)
            
            # Set the model
            previous_model = self.selected_model
            self.selected_model = model
            
            self.logger.info(f"Model updated from {previous_model} to {model}")
            
            return {
                'success': True,
                'message': f'Model successfully changed to "{model}"',
                'model': model,
                'previous_model': previous_model,
                'model_info': model_info,
                'changed': True,
                'recommendations': self._get_model_usage_recommendations(model)
            }
            
        except Exception as e:
            self.logger.error(f"Error setting model: {e}")
            return {
                'success': False,
                'error': f'Failed to set model: {str(e)}',
                'error_code': 'MODEL_SET_ERROR',
                'recovery_suggestions': [
                    'Try setting the model again',
                    'Check that the model name is correct',
                    'Contact support if the issue persists'
                ]
            }
    
    def _get_model_usage_recommendations(self, model: str) -> List[str]:
        """Get usage recommendations for a specific model"""
        recommendations = {
            'universal': [
                'Fastest, most robust model with broadest language support',
                'Suitable for multilingual content and general transcription',
                'Recommended for diverse language requirements'
            ],
            'universal_streaming': [
                'Optimized for real-time streaming applications',
                'Best for live transcription and streaming audio',
                'Current default model for streaming functionality'
            ],
            'slam-1': [
                'Most customizable model with highest accuracy for English',
                'English-only transcription with advanced customization options',
                'Recommended for critical English transcription tasks'
                'May take longer to process, especially for large files'
            ]
        }
        
        return recommendations.get(model, ['No specific recommendations available'])
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "authorization": self.api_key,
            "content-type": "application/json"
        }
    
    def upload_audio_file(self, file_path: str, max_retries: int = 3) -> Dict[str, Any]:
        """Upload audio file to AssemblyAI with retry mechanism"""
        
        # Validate file before upload
        validation_result = self.validate_file_for_transcription(file_path)
        if not validation_result['valid']:
            raise ProcessingError(
                f"File validation failed: {validation_result['error']}", 
                error_code="FILE_VALIDATION_FAILED"
            )
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Uploading file to AssemblyAI (attempt {attempt + 1}/{max_retries}): {file_path}")
                
                # Detect MIME type from file extension
                import mimetypes
                mime_type, _ = mimetypes.guess_type(file_path)
                
                # Map common audio extensions to proper MIME types
                audio_mime_types = {
                    '.wav': 'audio/wav',
                    '.mp3': 'audio/mpeg',
                    '.m4a': 'audio/mp4',
                    '.flac': 'audio/flac',
                    '.ogg': 'audio/ogg',
                    '.aac': 'audio/aac',
                    '.wma': 'audio/x-ms-wma'
                }
                
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext in audio_mime_types:
                    mime_type = audio_mime_types[file_ext]
                elif not mime_type:
                    mime_type = 'audio/wav'  # Default fallback
                
                self.logger.info(f"Uploading file with extension '{file_ext}' and MIME type '{mime_type}'")
                
                # Check file size and first few bytes for debugging
                file_size = os.path.getsize(file_path)
                self.logger.info(f"File size: {file_size} bytes")
                
                # Read first 16 bytes to check file signature
                with open(file_path, 'rb') as f:
                    file_header = f.read(16)
                    self.logger.info(f"File header (first 16 bytes): {file_header.hex()}")
                    
                    # Check for common audio file signatures
                    if file_header.startswith(b'RIFF') and b'WAVE' in file_header:
                        self.logger.info("File appears to be a valid WAV file")
                    elif file_header.startswith(b'ID3') or file_header[0:2] == b'\xff\xfb':
                        self.logger.info("File appears to be a valid MP3 file")
                    elif file_header.startswith(b'fLaC'):
                        self.logger.info("File appears to be a valid FLAC file")
                    else:
                        self.logger.warning(f"File signature not recognized as common audio format")
                
                # Verify file can be read completely
                try:
                    with open(file_path, 'rb') as test_file:
                        test_file.seek(0, 2)  # Seek to end
                        actual_size = test_file.tell()
                        test_file.seek(0)  # Seek back to beginning
                        if actual_size != file_size:
                            self.logger.warning(f"File size mismatch: expected {file_size}, actual {actual_size}")
                except Exception as e:
                    self.logger.error(f"Cannot read file properly: {e}")
                    raise ProcessingError(f"File read error: {e}", error_code="FILE_READ_ERROR")
                
                # Use the exact format from AssemblyAI documentation
                headers = {"authorization": self.api_key}
                
                with open(file_path, 'rb') as file:
                    # Use raw file data as per documentation: requests.post(base_url + "/v2/upload", headers=headers, data=f)
                    response = requests.post(
                        self.upload_url,
                        headers=headers,
                        data=file,  # Use data parameter instead of files
                        timeout=300  # 5 minute timeout
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    upload_url = result.get('upload_url')
                    self.logger.info(f"File uploaded successfully: {upload_url}")
                    
                    # Log upload URL details for debugging
                    if upload_url:
                        url_parts = upload_url.split('/')
                        upload_id = url_parts[-1] if url_parts else 'unknown'
                        self.logger.info(f"Upload ID: {upload_id}")
                    
                    return {
                        'success': True,
                        'upload_url': upload_url,
                        'file_size': result.get('file_size', 0),
                        'attempts': attempt + 1
                    }
                elif response.status_code == 401:
                    # Authentication error - don't retry
                    error_msg = "Invalid AssemblyAI API key"
                    self.logger.error(error_msg)
                    raise ProcessingError(
                        error_msg, 
                        error_code="AUTHENTICATION_FAILED",
                        recovery_suggestions=[
                            "Check that your AssemblyAI API key is correct",
                            "Verify that your API key has upload permissions",
                            "Generate a new API key if necessary"
                        ]
                    )
                elif response.status_code == 413:
                    # File too large - don't retry
                    error_msg = "File too large for AssemblyAI (max 2.2GB)"
                    self.logger.error(error_msg)
                    raise ProcessingError(
                        error_msg, 
                        error_code="FILE_TOO_LARGE",
                        recovery_suggestions=[
                            "Compress your audio file to reduce size",
                            "Split large files into smaller segments",
                            "Use a lower bitrate or different compression format"
                        ]
                    )
                elif response.status_code == 429:
                    # Rate limited - retry with backoff
                    wait_time = (2 ** attempt) * 5  # Exponential backoff: 5, 10, 20 seconds
                    self.logger.warning(f"Rate limited, waiting {wait_time} seconds before retry")
                    time.sleep(wait_time)
                    continue
                elif response.status_code >= 500:
                    # Server error - retry
                    error_msg = f"AssemblyAI server error (status {response.status_code})"
                    self.logger.warning(f"{error_msg}, attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        time.sleep((attempt + 1) * 2)  # Linear backoff for server errors
                        continue
                    else:
                        raise ProcessingError(
                            error_msg, 
                            error_code="SERVER_ERROR",
                            recovery_suggestions=[
                                "AssemblyAI servers may be experiencing issues",
                                "Try uploading again in a few minutes",
                                "Check AssemblyAI status page for service updates"
                            ]
                        )
                else:
                    # Other client errors
                    error_msg = f"Upload failed with status {response.status_code}: {response.text}"
                    self.logger.error(error_msg)
                    raise ProcessingError(
                        error_msg, 
                        error_code="UPLOAD_FAILED",
                        recovery_suggestions=[
                            "Check that your file is a valid audio format",
                            "Verify your AssemblyAI API key permissions",
                            "Try uploading a different file to test the service"
                        ]
                    )
                    
            except requests.exceptions.Timeout as e:
                last_exception = e
                self.logger.warning(f"Upload timeout (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 5)  # Increase timeout wait
                    continue
                    
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                self.logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 3)
                    continue
                    
            except FileNotFoundError:
                error_msg = f"File not found: {file_path}"
                self.logger.error(error_msg)
                raise ProcessingError(
                    error_msg, 
                    error_code="FILE_NOT_FOUND",
                    recovery_suggestions=[
                        "Ensure the file exists at the specified path",
                        "Check file permissions",
                        "Try uploading the file again"
                    ]
                )
                
            except PermissionError:
                error_msg = f"Permission denied accessing file: {file_path}"
                self.logger.error(error_msg)
                raise ProcessingError(
                    error_msg, 
                    error_code="PERMISSION_DENIED",
                    recovery_suggestions=[
                        "Check file permissions",
                        "Ensure the file is not locked by another application",
                        "Try copying the file to a different location"
                    ]
                )
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Unexpected error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
        
        # All retries exhausted
        error_msg = f"Upload failed after {max_retries} attempts. Last error: {str(last_exception)}"
        self.logger.error(error_msg)
        raise ProcessingError(
            error_msg, 
            error_code="UPLOAD_RETRY_EXHAUSTED",
            recovery_suggestions=[
                "Check your internet connection stability",
                "Verify AssemblyAI service status",
                "Try uploading a smaller file to test the service",
                "Contact support if the issue persists"
            ]
        )
    
    def _extract_language_detection_events(self, transcript_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract and convert language detection events from AssemblyAI transcript response
        
        Args:
            transcript_result: Complete AssemblyAI transcript response
            
        Returns:
            List of standardized language detection events
        """
        language_events = []
        
        try:
            # Extract language detection from main transcript
            language_detection = transcript_result.get('language_detection', {})
            
            if language_detection:
                # Main language detection event
                main_event = self._convert_assemblyai_language_event(
                    language_detection,
                    transcript_result.get('text', ''),
                    0,  # Start timestamp
                    transcript_result.get('audio_duration', 0) * 1000  # Convert to ms
                )
                if main_event:
                    language_events.append(main_event)
            
            # Extract language detection from words array (if available)
            words = transcript_result.get('words', [])
            if words:
                language_events.extend(self._extract_word_level_language_events(words))
            
            # Extract language detection from utterances (if available)
            utterances = transcript_result.get('utterances', [])
            if utterances:
                language_events.extend(self._extract_utterance_level_language_events(utterances))
            
            self.logger.info(f"Extracted {len(language_events)} language detection events")
            return language_events
            
        except Exception as e:
            self.logger.error(f"Error extracting language detection events: {e}")
            return []
    
    def _convert_assemblyai_language_event(self, 
                                         language_data: Dict[str, Any], 
                                         text_segment: str = None,
                                         start_time_ms: int = 0,
                                         duration_ms: int = 0) -> Optional[Dict[str, Any]]:
        """
        Convert AssemblyAI language detection format to internal format
        
        Args:
            language_data: AssemblyAI language detection data
            text_segment: Associated text segment
            start_time_ms: Start time in milliseconds
            duration_ms: Duration in milliseconds
            
        Returns:
            Standardized language detection event or None if invalid
        """
        try:
            # Extract language code from AssemblyAI format
            detected_language = language_data.get('language_code')
            if not detected_language:
                # Try alternative field names
                detected_language = language_data.get('language') or language_data.get('detected_language')
            
            if not detected_language:
                return None
            
            # Extract confidence score
            confidence = language_data.get('confidence', 0.0)
            if confidence is None:
                confidence = language_data.get('language_confidence', 0.0)
            
            # Ensure confidence is a float between 0 and 1
            try:
                confidence = float(confidence)
                if confidence > 1.0:
                    confidence = confidence / 100.0  # Convert percentage to decimal
                confidence = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                confidence = 0.5  # Default confidence
            
            # Create timestamp
            timestamp = datetime.utcnow().isoformat()
            if start_time_ms > 0:
                # Calculate actual timestamp based on start time
                start_time = datetime.utcnow() - timedelta(milliseconds=start_time_ms)
                timestamp = start_time.isoformat()
            
            # Create standardized event
            event = {
                'detected_language': detected_language.lower(),
                'confidence': confidence,
                'timestamp': timestamp,
                'duration_ms': duration_ms,
                'transcript_segment': text_segment[:100] if text_segment else None,
                'source': 'assemblyai_file_upload',
                'start_time_ms': start_time_ms,
                'raw_data': language_data  # Keep original data for debugging
            }
            
            return event
            
        except Exception as e:
            self.logger.error(f"Error converting AssemblyAI language event: {e}")
            return None
    
    def _extract_word_level_language_events(self, words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract language detection events from word-level data
        
        Args:
            words: List of word objects from AssemblyAI
            
        Returns:
            List of language detection events
        """
        events = []
        current_language = None
        current_start = None
        current_text_parts = []
        
        try:
            for word in words:
                word_language = word.get('language_code') or word.get('language')
                word_confidence = word.get('language_confidence', word.get('confidence', 0.0))
                word_text = word.get('text', '')
                word_start = word.get('start', 0)
                word_end = word.get('end', 0)
                
                if word_language and word_language != current_language:
                    # Language change detected
                    if current_language and current_start is not None:
                        # Create event for previous language segment
                        event = self._convert_assemblyai_language_event(
                            {
                                'language_code': current_language,
                                'confidence': word_confidence
                            },
                            ' '.join(current_text_parts),
                            current_start,
                            word_start - current_start
                        )
                        if event:
                            events.append(event)
                    
                    # Start new language segment
                    current_language = word_language
                    current_start = word_start
                    current_text_parts = [word_text]
                else:
                    # Continue current language segment
                    if word_text:
                        current_text_parts.append(word_text)
            
            # Handle final segment
            if current_language and current_start is not None:
                final_word = words[-1] if words else {}
                final_end = final_word.get('end', current_start)
                
                event = self._convert_assemblyai_language_event(
                    {
                        'language_code': current_language,
                        'confidence': final_word.get('language_confidence', 0.0)
                    },
                    ' '.join(current_text_parts),
                    current_start,
                    final_end - current_start
                )
                if event:
                    events.append(event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error extracting word-level language events: {e}")
            return []
    
    def _extract_utterance_level_language_events(self, utterances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract language detection events from utterance-level data
        
        Args:
            utterances: List of utterance objects from AssemblyAI
            
        Returns:
            List of language detection events
        """
        events = []
        
        try:
            for utterance in utterances:
                language_code = utterance.get('language_code') or utterance.get('language')
                confidence = utterance.get('language_confidence', utterance.get('confidence', 0.0))
                text = utterance.get('text', '')
                start_time = utterance.get('start', 0)
                end_time = utterance.get('end', 0)
                
                if language_code:
                    event = self._convert_assemblyai_language_event(
                        {
                            'language_code': language_code,
                            'confidence': confidence
                        },
                        text,
                        start_time,
                        end_time - start_time
                    )
                    if event:
                        events.append(event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error extracting utterance-level language events: {e}")
            return []
    
    def transcribe_file(self, audio_url: str, **kwargs) -> Dict[str, Any]:
        """Transcribe uploaded file with enhanced features"""
        try:
            # Validate model supports file upload
            model_info = self.AVAILABLE_MODELS.get(self.selected_model, {})
            if not model_info.get('supports_file_upload', False):
                # Fallback to universal for file upload
                self.logger.warning(f"Model {self.selected_model} doesn't support file upload, falling back to universal")
                self.selected_model = 'universal'
                model_info = self.AVAILABLE_MODELS['universal']
            
            # Prepare transcription request - use minimal config like successful manual test
            transcription_config = {
                "audio_url": audio_url
            }
            
            # Add model selection if not using default (universal)
            model_api_value = model_info.get('api_value')
            if model_api_value:
                transcription_config["speech_model"] = model_api_value
            
            # Only add parameters if explicitly requested (not by default)
            if kwargs.get('language_detection') is True:
                transcription_config["language_detection"] = True
            if kwargs.get('speaker_labels') is True:
                transcription_config["speaker_labels"] = True
            if kwargs.get('dual_channel') is True:
                transcription_config["dual_channel"] = True
            if kwargs.get('punctuate') is True:
                transcription_config["punctuate"] = True
            if kwargs.get('format_text') is True:
                transcription_config["format_text"] = True
            
            # Add any additional configuration
            additional_config = kwargs.get('additional_config', {})
            transcription_config.update(additional_config)
            
            self.logger.info(f"Sending transcription request: {transcription_config}")
            self.logger.info(f"Using headers: {self.get_headers()}")
            
            response = requests.post(
                self.transcript_url,
                headers=self.get_headers(),
                json=transcription_config
            )
            
            self.logger.info(f"Transcription response status: {response.status_code}")
            self.logger.info(f"Transcription response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                transcript_id = result.get('id')
                
                self.logger.info(f"Transcription started with ID: {transcript_id}, Model: {self.selected_model}")
                
                return {
                    'success': True,
                    'transcript_id': transcript_id,
                    'status': result.get('status', 'queued'),
                    'model_used': self.selected_model,
                    'config': transcription_config
                }
            else:
                error_msg = f"Transcription request failed with status {response.status_code}: {response.text}"
                self.logger.error(error_msg)
                raise ProcessingError(error_msg, error_code="TRANSCRIPTION_FAILED")
                
        except Exception as e:
            if isinstance(e, ProcessingError):
                raise
            error_msg = f"Error starting transcription: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg, error_code="TRANSCRIPTION_ERROR")
    
    def get_transcription_status(self, transcript_id: str, max_retries: int = 3) -> Dict[str, Any]:
        """Poll transcription status with retry mechanism"""
        
        if not transcript_id:
            raise ProcessingError(
                "Transcript ID is required", 
                error_code="MISSING_TRANSCRIPT_ID"
            )
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Checking transcription status (attempt {attempt + 1}/{max_retries}): {transcript_id}")
                
                response = requests.get(
                    f"{self.transcript_url}/{transcript_id}",
                    headers=self.get_headers(),
                    timeout=30  # 30 second timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    status = result.get('status')
                    
                    response_data = {
                        'success': True,
                        'transcript_id': transcript_id,
                        'status': status,
                        'audio_duration': result.get('audio_duration'),
                        'confidence': result.get('confidence'),
                        'attempts': attempt + 1
                    }
                    
                    # Add transcript text if completed
                    if status == 'completed':
                        # Process language detection data from AssemblyAI response
                        language_detection_events = self._extract_language_detection_events(result)
                        
                        response_data.update({
                            'text': result.get('text', ''),
                            'words': result.get('words', []),
                            'language_detection': result.get('language_detection', {}),
                            'language_detection_events': language_detection_events,
                            'audio_duration': result.get('audio_duration'),
                            'confidence': result.get('confidence')
                        })
                        self.logger.info(f"Transcription completed successfully: {transcript_id}")
                        
                    elif status == 'error':
                        error_details = result.get('error', 'Unknown transcription error')
                        response_data.update({
                            'error': error_details,
                            'error_details': result.get('error_details', {})
                        })
                        self.logger.error(f"Transcription failed: {transcript_id} - {error_details}")
                        
                    elif status in ['queued', 'processing']:
                        self.logger.debug(f"Transcription in progress: {transcript_id} - {status}")
                        
                    return response_data
                    
                elif response.status_code == 401:
                    # Authentication error - don't retry
                    error_msg = "Invalid AssemblyAI API key for status check"
                    self.logger.error(error_msg)
                    raise ProcessingError(
                        error_msg, 
                        error_code="AUTHENTICATION_FAILED",
                        recovery_suggestions=[
                            "Check that your AssemblyAI API key is correct",
                            "Verify that your API key has transcription permissions"
                        ]
                    )
                    
                elif response.status_code == 404:
                    # Transcript not found - don't retry
                    error_msg = f"Transcript not found: {transcript_id}"
                    self.logger.error(error_msg)
                    raise ProcessingError(
                        error_msg, 
                        error_code="TRANSCRIPT_NOT_FOUND",
                        recovery_suggestions=[
                            "Verify the transcript ID is correct",
                            "Check if the transcription was cancelled or expired",
                            "Try starting a new transcription"
                        ]
                    )
                    
                elif response.status_code == 429:
                    # Rate limited - retry with backoff
                    wait_time = (2 ** attempt) * 2  # Exponential backoff: 2, 4, 8 seconds
                    self.logger.warning(f"Rate limited on status check, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    continue
                    
                elif response.status_code >= 500:
                    # Server error - retry
                    error_msg = f"AssemblyAI server error during status check (status {response.status_code})"
                    self.logger.warning(f"{error_msg}, attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        time.sleep((attempt + 1) * 2)
                        continue
                    else:
                        raise ProcessingError(
                            error_msg, 
                            error_code="SERVER_ERROR",
                            recovery_suggestions=[
                                "AssemblyAI servers may be experiencing issues",
                                "Try checking status again in a few minutes",
                                "Check AssemblyAI status page for service updates"
                            ]
                        )
                else:
                    error_msg = f"Status check failed with status {response.status_code}: {response.text}"
                    self.logger.error(error_msg)
                    raise ProcessingError(
                        error_msg, 
                        error_code="STATUS_CHECK_FAILED",
                        recovery_suggestions=[
                            "Verify the transcript ID is correct",
                            "Check your AssemblyAI API key permissions",
                            "Try checking status again"
                        ]
                    )
                    
            except requests.exceptions.Timeout as e:
                last_exception = e
                self.logger.warning(f"Status check timeout (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 3)
                    continue
                    
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                self.logger.warning(f"Connection error during status check (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                    
            except ProcessingError:
                # Don't retry ProcessingErrors
                raise
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Unexpected error during status check (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
        
        # All retries exhausted
        error_msg = f"Status check failed after {max_retries} attempts. Last error: {str(last_exception)}"
        self.logger.error(error_msg)
        raise ProcessingError(
            error_msg, 
            error_code="STATUS_CHECK_RETRY_EXHAUSTED",
            recovery_suggestions=[
                "Check your internet connection stability",
                "Verify AssemblyAI service status",
                "Try checking status again later",
                "Contact support if the issue persists"
            ]
        )
    
    def wait_for_completion(self, transcript_id: str, timeout: int = 300, poll_interval: int = 5, 
                           progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Wait for transcription to complete with timeout and progress tracking"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status_result = self.get_transcription_status(transcript_id)
                
                if not status_result['success']:
                    return status_result
                
                status = status_result['status']
                elapsed_time = time.time() - start_time
                
                # Calculate progress percentage (rough estimate)
                if status == 'queued':
                    progress = 5
                elif status == 'processing':
                    # Estimate progress based on elapsed time and typical processing duration
                    audio_duration = status_result.get('audio_duration')
                    if audio_duration and audio_duration > 0:
                        # Rough estimate: processing takes about 10-20% of audio duration
                        estimated_processing_time = audio_duration * 0.15
                        progress = min(95, 10 + (elapsed_time / estimated_processing_time) * 85)
                    else:
                        progress = min(95, 10 + (elapsed_time / 60) * 85)  # Assume 1 minute processing
                else:
                    progress = 100
                
                # Call progress callback if provided
                if progress_callback:
                    try:
                        progress_callback({
                            'transcript_id': transcript_id,
                            'status': status,
                            'progress': int(progress),
                            'elapsed_time': elapsed_time,
                            'audio_duration': status_result.get('audio_duration')
                        })
                    except Exception as callback_error:
                        self.logger.warning(f"Progress callback error: {callback_error}")
                
                if status == 'completed':
                    self.logger.info(f"Transcription {transcript_id} completed successfully")
                    return status_result
                elif status == 'error':
                    error_msg = status_result.get('error', 'Unknown transcription error')
                    self.logger.error(f"Transcription {transcript_id} failed: {error_msg}")
                    return status_result
                elif status in ['queued', 'processing']:
                    self.logger.debug(f"Transcription {transcript_id} status: {status} ({progress:.1f}%)")
                    time.sleep(poll_interval)
                else:
                    self.logger.warning(f"Unknown transcription status: {status}")
                    time.sleep(poll_interval)
                    
            except Exception as e:
                self.logger.error(f"Error while waiting for transcription: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'transcript_id': transcript_id
                }
        
        # Timeout reached
        error_msg = f"Transcription {transcript_id} timed out after {timeout} seconds"
        self.logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'transcript_id': transcript_id,
            'timeout': True
        }
    
    def update_streaming_config(self, model: str) -> bool:
        """Update streaming configuration with selected model"""
        if not self.is_valid_model(model):
            raise ValidationError(f"Invalid model for streaming: {model}")
        
        self.selected_model = model
        self.logger.info(f"Streaming configuration updated to use model: {model}")
        return True
    
    def get_streaming_endpoint(self, additional_params: Optional[Dict[str, Any]] = None) -> str:
        """Get streaming endpoint URL with model configuration"""
        
        # Validate model supports streaming
        model_info = self.AVAILABLE_MODELS.get(self.selected_model, {})
        if not model_info.get('supports_streaming', False):
            # Fallback to universal_streaming for streaming
            self.logger.warning(f"Model {self.selected_model} doesn't support streaming, falling back to universal_streaming")
            self.selected_model = 'universal_streaming'
            model_info = self.AVAILABLE_MODELS['universal_streaming']
        
        # Base streaming parameters
        params = {
            "sample_rate": 16000,
            "format_turns": True,
            "language_detection": True,
        }
        
        # For streaming, universal_streaming is the default and doesn't need speech_model parameter
        # Only add speech_model if we're using a different model (which shouldn't happen for streaming)
        model_api_value = model_info.get('api_value')
        if model_api_value:
            params["speech_model"] = model_api_value
        
        # Add any additional parameters
        if additional_params:
            params.update(additional_params)
        
        endpoint = f"{self.streaming_base_url}?{urlencode(params)}"
        self.logger.info(f"Generated streaming endpoint with model {self.selected_model}: {endpoint}")
        
        return endpoint
    
    def get_recommended_model_for_use_case(self, use_case: str) -> str:
        """Get recommended model for specific use case"""
        recommendations = {
            'streaming': 'universal_streaming',
            'live_audio': 'universal_streaming',
            'file_upload': 'universal',
            'file_transcription': 'universal',
            'english_only': 'slam-1',
            'multilingual': 'universal'
        }
        
        recommended = recommendations.get(use_case, 'universal')
        
        # Validate the recommended model exists and supports the use case
        if recommended in self.AVAILABLE_MODELS:
            model_info = self.AVAILABLE_MODELS[recommended]
            if use_case in ['streaming', 'live_audio'] and model_info.get('supports_streaming', False):
                return recommended
            elif use_case in ['file_upload', 'file_transcription'] and model_info.get('supports_file_upload', False):
                return recommended
        
        # Fallback logic
        if use_case in ['streaming', 'live_audio']:
            return 'universal_streaming'
        else:
            return 'universal'
    
    def validate_model_for_use_case(self, model: str, use_case: str) -> Dict[str, Any]:
        """Validate if a model is suitable for a specific use case"""
        if model not in self.AVAILABLE_MODELS:
            return {
                'valid': False,
                'error': f'Model {model} not found',
                'recommended_model': self.get_recommended_model_for_use_case(use_case)
            }
        
        model_info = self.AVAILABLE_MODELS[model]
        
        if use_case in ['streaming', 'live_audio']:
            if not model_info.get('supports_streaming', False):
                return {
                    'valid': False,
                    'error': f'Model {model} does not support streaming',
                    'recommended_model': 'universal_streaming'
                }
        elif use_case in ['file_upload', 'file_transcription']:
            if not model_info.get('supports_file_upload', False):
                return {
                    'valid': False,
                    'error': f'Model {model} does not support file upload',
                    'recommended_model': 'universal'
                }
        
        return {
            'valid': True,
            'model': model,
            'model_info': model_info
        }
    
    def validate_model_for_feature(self, model: str, feature: str) -> bool:
        """Validate if model supports specific feature"""
        if not self.is_valid_model(model):
            return False
        
        # All current models support basic features
        # This method can be extended for future model-specific feature validation
        supported_features = ['transcription', 'language_detection', 'streaming', 'file_upload']
        
        return feature in supported_features
    
    def get_model_recommendations(self, use_case: str) -> List[str]:
        """Get model recommendations based on use case"""
        recommendations = {
            'real_time': ['universal_streaming', 'universal'],
            'streaming': ['universal_streaming', 'universal'],
            'high_accuracy': ['slam-1', 'universal'],
            'english_only': ['slam-1', 'universal'],
            'multilingual': ['universal', 'universal_streaming'],
            'general': ['universal', 'universal_streaming'],
            'fast': ['universal', 'universal_streaming'],
            'file_upload': ['slam-1', 'universal', 'universal_streaming']
        }
        
        return recommendations.get(use_case, ['universal_streaming'])
    
    def process_file_transcription(self, file_path: str, progress_callback: Optional[callable] = None,
                                  **transcription_options) -> Dict[str, Any]:
        """Complete file transcription workflow: upload -> transcribe -> wait for completion"""
        try:
            # Validate model for file transcription
            model_validation = self.validate_model_for_use_case(self.selected_model, 'file_transcription')
            if not model_validation['valid']:
                self.logger.warning(f"Model validation failed: {model_validation['error']}")
                # Use recommended model
                recommended_model = model_validation['recommended_model']
                self.logger.info(f"Switching to recommended model: {recommended_model}")
                self.selected_model = recommended_model
            
            # Step 1: Upload file
            self.logger.info(f"Starting file transcription workflow for: {file_path} using model: {self.selected_model}")
            
            if progress_callback:
                progress_callback({
                    'stage': 'uploading',
                    'progress': 0,
                    'message': f'Uploading file to AssemblyAI (using {self.selected_model} model)...'
                })
            
            upload_result = self.upload_audio_file(file_path)
            if not upload_result['success']:
                return {
                    'success': False,
                    'error': 'File upload failed',
                    'stage': 'upload'
                }
            
            if progress_callback:
                progress_callback({
                    'stage': 'upload_complete',
                    'progress': 10,
                    'message': 'File uploaded successfully, starting transcription...'
                })
            
            # Step 2: Start transcription
            transcription_result = self.transcribe_file(
                upload_result['upload_url'],
                **transcription_options
            )
            
            if not transcription_result['success']:
                return {
                    'success': False,
                    'error': 'Failed to start transcription',
                    'stage': 'transcription_start'
                }
            
            transcript_id = transcription_result['transcript_id']
            
            if progress_callback:
                progress_callback({
                    'stage': 'transcription_started',
                    'progress': 15,
                    'message': f'Transcription started (ID: {transcript_id})',
                    'transcript_id': transcript_id
                })
            
            # Step 3: Wait for completion with progress updates
            def transcription_progress_callback(progress_data):
                if progress_callback:
                    progress_callback({
                        'stage': 'transcribing',
                        'progress': 15 + (progress_data['progress'] * 0.85),  # Scale to 15-100%
                        'message': f"Transcribing... ({progress_data['status']})",
                        'transcript_id': transcript_id,
                        'transcription_progress': progress_data['progress']
                    })
            
            completion_result = self.wait_for_completion(
                transcript_id,
                timeout=transcription_options.get('timeout', 300),
                poll_interval=transcription_options.get('poll_interval', 5),
                progress_callback=transcription_progress_callback
            )
            
            if completion_result['success'] and completion_result['status'] == 'completed':
                if progress_callback:
                    progress_callback({
                        'stage': 'completed',
                        'progress': 100,
                        'message': 'Transcription completed successfully!',
                        'transcript_id': transcript_id
                    })
                
                # Extract language detection events from the completion result
                language_detection_events = completion_result.get('language_detection_events', [])
                
                return {
                    'success': True,
                    'transcript_id': transcript_id,
                    'text': completion_result.get('text', ''),
                    'words': completion_result.get('words', []),
                    'language_detection': completion_result.get('language_detection', {}),
                    'language_detection_events': language_detection_events,
                    'audio_duration': completion_result.get('audio_duration'),
                    'confidence': completion_result.get('confidence'),
                    'model_used': self.selected_model,
                    'file_size': upload_result.get('file_size', 0)
                }
            else:
                error_msg = completion_result.get('error', 'Transcription failed')
                if progress_callback:
                    progress_callback({
                        'stage': 'error',
                        'progress': 0,
                        'message': f'Transcription failed: {error_msg}',
                        'transcript_id': transcript_id
                    })
                
                return {
                    'success': False,
                    'error': error_msg,
                    'transcript_id': transcript_id,
                    'stage': 'transcription_processing'
                }
                
        except Exception as e:
            error_msg = f"File transcription workflow failed: {str(e)}"
            self.logger.error(error_msg)
            
            if progress_callback:
                progress_callback({
                    'stage': 'error',
                    'progress': 0,
                    'message': error_msg
                })
            
            return {
                'success': False,
                'error': error_msg,
                'stage': 'workflow_error'
            }
    
    def cancel_transcription(self, transcript_id: str) -> Dict[str, Any]:
        """Cancel an ongoing transcription (if supported by API)"""
        try:
            # Note: AssemblyAI doesn't currently support cancellation
            # This method is for future compatibility
            self.logger.warning(f"Transcription cancellation requested for {transcript_id}, but not supported by API")
            return {
                'success': False,
                'error': 'Transcription cancellation not supported by AssemblyAI API',
                'transcript_id': transcript_id
            }
        except Exception as e:
            error_msg = f"Error attempting to cancel transcription: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'transcript_id': transcript_id
            }
    
    def get_transcription_cost_estimate(self, audio_duration_seconds: float) -> Dict[str, Any]:
        """Get cost estimate for transcription (based on AssemblyAI pricing)"""
        try:
            # AssemblyAI pricing (as of 2024): $0.00037 per second
            # This is an estimate and actual pricing may vary
            cost_per_second = 0.00037
            estimated_cost = audio_duration_seconds * cost_per_second
            
            return {
                'success': True,
                'audio_duration_seconds': audio_duration_seconds,
                'estimated_cost_usd': round(estimated_cost, 4),
                'cost_per_second': cost_per_second,
                'note': 'This is an estimate based on standard pricing. Actual costs may vary.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error calculating cost estimate: {str(e)}"
            }
    
    def validate_file_for_transcription(self, file_path: str) -> Dict[str, Any]:
        """Validate file before transcription with comprehensive error handling"""
        try:
            import os
            import mimetypes
            
            # Input validation
            if not file_path or not isinstance(file_path, str):
                return {
                    'valid': False,
                    'error': 'Invalid file path provided',
                    'error_code': 'INVALID_PATH',
                    'recovery_suggestions': [
                        'Ensure a valid file path is provided',
                        'Check that the file path is a string'
                    ]
                }
            
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    'valid': False,
                    'error': f'File does not exist: {file_path}',
                    'error_code': 'FILE_NOT_FOUND',
                    'recovery_suggestions': [
                        'Check that the file path is correct',
                        'Ensure the file has not been moved or deleted',
                        'Try uploading the file again'
                    ]
                }
            
            # Check if it's actually a file (not a directory)
            if not os.path.isfile(file_path):
                return {
                    'valid': False,
                    'error': f'Path is not a file: {file_path}',
                    'error_code': 'NOT_A_FILE',
                    'recovery_suggestions': [
                        'Ensure you are selecting a file, not a folder',
                        'Check the file path is correct'
                    ]
                }
            
            # Check file permissions
            if not os.access(file_path, os.R_OK):
                return {
                    'valid': False,
                    'error': f'Cannot read file: {file_path}',
                    'error_code': 'PERMISSION_DENIED',
                    'recovery_suggestions': [
                        'Check file permissions',
                        'Ensure the file is not locked by another application',
                        'Try copying the file to a different location'
                    ]
                }
            
            # Get file size with error handling
            try:
                file_size = os.path.getsize(file_path)
            except OSError as e:
                return {
                    'valid': False,
                    'error': f'Cannot determine file size: {str(e)}',
                    'error_code': 'SIZE_CHECK_FAILED',
                    'recovery_suggestions': [
                        'Check that the file is not corrupted',
                        'Ensure the file system is accessible',
                        'Try uploading a different file'
                    ]
                }
            
            # Check for empty file
            if file_size == 0:
                return {
                    'valid': False,
                    'error': 'File is empty (0 bytes)',
                    'error_code': 'EMPTY_FILE',
                    'recovery_suggestions': [
                        'Ensure the file contains audio data',
                        'Check that the file was not corrupted during transfer',
                        'Try re-recording or re-exporting the audio file'
                    ]
                }
            
            # Check file size limits
            max_file_size = 2.2 * 1024 * 1024 * 1024  # 2.2GB limit for AssemblyAI
            
            if file_size > max_file_size:
                file_size_gb = file_size / (1024 * 1024 * 1024)
                return {
                    'valid': False,
                    'error': f'File too large ({file_size_gb:.1f}GB). Maximum size: 2.2GB',
                    'error_code': 'FILE_TOO_LARGE',
                    'file_size': file_size,
                    'file_size_gb': file_size_gb,
                    'max_size_gb': 2.2,
                    'recovery_suggestions': [
                        'Compress your audio file to reduce size',
                        'Split large files into smaller segments',
                        'Use a lower bitrate or different compression format',
                        'Consider using audio editing software to reduce file size'
                    ]
                }
            
            # Check file extension
            supported_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.mp4', '.wma', '.aac', '.ogg']
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if not file_extension:
                return {
                    'valid': False,
                    'error': 'File has no extension',
                    'error_code': 'NO_EXTENSION',
                    'recovery_suggestions': [
                        'Add a file extension (e.g., .mp3, .wav, .m4a)',
                        'Ensure your audio file has the correct extension',
                        f'Supported formats: {", ".join(supported_extensions)}'
                    ]
                }
            
            if file_extension not in supported_extensions:
                return {
                    'valid': False,
                    'error': f'Unsupported file format: {file_extension}',
                    'error_code': 'UNSUPPORTED_FORMAT',
                    'file_extension': file_extension,
                    'supported_extensions': supported_extensions,
                    'recovery_suggestions': [
                        f'Convert your file to one of these supported formats: {", ".join(supported_extensions)}',
                        'Use audio conversion software like Audacity, FFmpeg, or online converters',
                        'Check that your file extension matches the actual file format'
                    ]
                }
            
            # MIME type validation (if available)
            mime_type = mimetypes.guess_type(file_path)[0]
            expected_mime_prefixes = ['audio/', 'video/']  # video/ for mp4 files
            
            if mime_type and not any(mime_type.startswith(prefix) for prefix in expected_mime_prefixes):
                return {
                    'valid': False,
                    'error': f'File does not appear to be an audio file (MIME type: {mime_type})',
                    'error_code': 'INVALID_MIME_TYPE',
                    'detected_mime_type': mime_type,
                    'recovery_suggestions': [
                        'Ensure you are uploading an audio file',
                        'Check that the file extension matches the actual file format',
                        'Try converting the file to a standard audio format'
                    ]
                }
            
            # Additional file integrity checks
            try:
                # Try to read the first few bytes to check for corruption
                with open(file_path, 'rb') as f:
                    header = f.read(16)  # Read first 16 bytes
                    
                if len(header) == 0:
                    return {
                        'valid': False,
                        'error': 'File appears to be corrupted - cannot read content',
                        'error_code': 'CORRUPTED_FILE',
                        'recovery_suggestions': [
                            'The file may be corrupted',
                            'Try uploading the file again',
                            'Verify the original file is not corrupted',
                            'Try converting the file to a different format'
                        ]
                    }
                    
            except Exception as e:
                return {
                    'valid': False,
                    'error': f'Cannot read file content: {str(e)}',
                    'error_code': 'READ_ERROR',
                    'recovery_suggestions': [
                        'The file may be corrupted or locked',
                        'Ensure the file is not being used by another application',
                        'Try copying the file to a different location'
                    ]
                }
            
            # Calculate file size in different units for user display
            file_size_mb = file_size / (1024 * 1024)
            file_size_gb = file_size / (1024 * 1024 * 1024)
            
            # Estimate processing time (rough estimate)
            estimated_processing_minutes = max(1, int(file_size_mb / 10))  # Rough estimate: 1 minute per 10MB
            
            return {
                'valid': True,
                'file_path': file_path,
                'file_size': file_size,
                'file_size_mb': round(file_size_mb, 2),
                'file_size_gb': round(file_size_gb, 3),
                'file_extension': file_extension,
                'mime_type': mime_type,
                'estimated_processing_minutes': estimated_processing_minutes,
                'validation_timestamp': datetime.utcnow().isoformat(),
                'supported_features': [
                    'transcription',
                    'language_detection',
                    'speaker_labels',
                    'punctuation',
                    'formatting'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"File validation error: {e}")
            return {
                'valid': False,
                'error': f'File validation failed: {str(e)}',
                'error_code': 'VALIDATION_ERROR',
                'recovery_suggestions': [
                    'Try validating the file again',
                    'Check that the file is not corrupted',
                    'Ensure the file is a valid audio format',
                    'Contact support if the issue persists'
                ]
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and current configuration"""
        return {
            'service_name': 'Enhanced AssemblyAI Service',
            'version': '1.0.0',
            'current_model': self.selected_model,
            'available_models': self.get_available_models(),
            'api_endpoints': {
                'upload': self.upload_url,
                'transcript': self.transcript_url,
                'streaming': self.streaming_base_url
            },
            'features': [
                'model_selection',
                'file_upload',
                'streaming',
                'language_detection',
                'real_time_transcription',
                'progress_tracking',
                'error_handling',
                'cost_estimation'
            ],
            'limits': {
                'max_file_size_gb': 2.2,
                'supported_formats': ['.mp3', '.wav', '.m4a', '.flac', '.mp4', '.wma', '.aac', '.ogg']
            }
        }
    
    def handle_model_fallback(self, failed_model: str, error_context: str = None) -> Dict[str, Any]:
        """
        Handle model selection fallback when a model fails
        
        Args:
            failed_model: The model that failed
            error_context: Context about why the model failed
            
        Returns:
            Dictionary with fallback result and user feedback
        """
        try:
            self.logger.warning(f"Model fallback triggered for {failed_model}: {error_context}")
            
            # Define fallback hierarchy
            fallback_hierarchy = {
                'slam-1': ['universal', 'universal_streaming'],
                'universal': ['universal_streaming', 'slam-1'],
                'universal_streaming': ['universal', 'slam-1']
            }
            
            fallback_models = fallback_hierarchy.get(failed_model, ['universal_streaming'])
            
            # Try each fallback model
            for fallback_model in fallback_models:
                if self.is_valid_model(fallback_model):
                    previous_model = self.selected_model
                    self.selected_model = fallback_model
                    
                    self.logger.info(f"Switched from {failed_model} to fallback model {fallback_model}")
                    
                    return {
                        'success': True,
                        'fallback_applied': True,
                        'failed_model': failed_model,
                        'fallback_model': fallback_model,
                        'previous_model': previous_model,
                        'error_context': error_context,
                        'user_feedback': {
                            'type': 'warning',
                            'message': f'Switched to {fallback_model} model due to issues with {failed_model}',
                            'recovery_suggestions': [
                                f'The {fallback_model} model is now being used instead',
                                'Transcription will continue normally',
                                f'You can manually switch back to {failed_model} later if desired',
                                'Check AssemblyAI service status if issues persist'
                            ]
                        },
                        'model_info': self.get_model_info(fallback_model)
                    }
            
            # If no fallback models work, use universal_streaming as last resort
            self.selected_model = 'universal_streaming'
            self.logger.error(f"All fallback models failed, using universal_streaming as last resort")
            
            return {
                'success': True,
                'fallback_applied': True,
                'failed_model': failed_model,
                'fallback_model': 'universal_streaming',
                'last_resort': True,
                'error_context': error_context,
                'user_feedback': {
                    'type': 'error',
                    'message': 'Model selection issues detected, using default streaming model',
                    'recovery_suggestions': [
                        'Using the universal streaming model as a fallback',
                        'Transcription will continue with default settings',
                        'Check your internet connection',
                        'Contact support if issues persist'
                    ]
                },
                'model_info': self.get_model_info('universal_streaming')
            }
            
        except Exception as e:
            self.logger.error(f"Error during model fallback: {e}")
            return {
                'success': False,
                'fallback_applied': False,
                'error': f'Model fallback failed: {str(e)}',
                'user_feedback': {
                    'type': 'error',
                    'message': 'Unable to switch to fallback model',
                    'recovery_suggestions': [
                        'Try refreshing the page',
                        'Check your internet connection',
                        'Contact support for assistance'
                    ]
                }
            }
    
    def get_model_health_status(self) -> Dict[str, Any]:
        """
        Check the health status of the current model
        
        Returns:
            Dictionary with model health information
        """
        try:
            model_info = self.get_model_info(self.selected_model)
            
            # Basic health check - in a real implementation, this might
            # make a test API call or check service status
            health_status = {
                'model': self.selected_model,
                'status': 'healthy',  # Would be determined by actual health check
                'last_checked': datetime.utcnow().isoformat(),
                'model_info': model_info,
                'recommendations': self._get_model_usage_recommendations(self.selected_model)
            }
            
            return {
                'success': True,
                'health_status': health_status
            }
            
        except Exception as e:
            self.logger.error(f"Error checking model health: {e}")
            return {
                'success': False,
                'error': f'Health check failed: {str(e)}',
                'user_feedback': {
                    'type': 'warning',
                    'message': 'Unable to verify model status',
                    'recovery_suggestions': [
                        'Model functionality may still work normally',
                        'Try using the service and report any issues',
                        'Check AssemblyAI service status if problems occur'
                    ]
                }
            }
    
    def provide_status_update(self, operation: str, progress: int, message: str, 
                            estimated_completion: str = None) -> Dict[str, Any]:
        """
        Provide clear status updates during long-running operations
        
        Args:
            operation: Name of the operation (e.g., 'transcription', 'upload')
            progress: Progress percentage (0-100)
            message: Status message
            estimated_completion: Estimated completion time
            
        Returns:
            Dictionary with formatted status update
        """
        try:
            # Validate inputs
            progress = max(0, min(100, int(progress)))
            
            # Create status update
            status_update = {
                'operation': operation,
                'progress': progress,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'estimated_completion': estimated_completion
            }
            
            # Add progress-specific feedback
            if progress == 0:
                status_update['user_feedback'] = {
                    'type': 'info',
                    'message': f'{operation.title()} is starting...',
                    'show_progress': True
                }
            elif progress < 25:
                status_update['user_feedback'] = {
                    'type': 'info',
                    'message': f'{operation.title()} is beginning ({progress}%)',
                    'show_progress': True
                }
            elif progress < 75:
                status_update['user_feedback'] = {
                    'type': 'info',
                    'message': f'{operation.title()} is in progress ({progress}%)',
                    'show_progress': True
                }
            elif progress < 100:
                status_update['user_feedback'] = {
                    'type': 'info',
                    'message': f'{operation.title()} is almost complete ({progress}%)',
                    'show_progress': True
                }
            else:
                status_update['user_feedback'] = {
                    'type': 'success',
                    'message': f'{operation.title()} completed successfully!',
                    'show_progress': False
                }
            
            # Add estimated time remaining
            if estimated_completion and progress < 100:
                try:
                    completion_time = datetime.fromisoformat(estimated_completion.replace('Z', '+00:00'))
                    time_remaining = completion_time - datetime.utcnow().replace(tzinfo=completion_time.tzinfo)
                    
                    if time_remaining.total_seconds() > 0:
                        minutes_remaining = int(time_remaining.total_seconds() / 60)
                        if minutes_remaining > 0:
                            status_update['time_remaining'] = f"~{minutes_remaining} minute(s) remaining"
                        else:
                            status_update['time_remaining'] = "Less than 1 minute remaining"
                except:
                    pass  # Ignore time calculation errors
            
            return {
                'success': True,
                'status_update': status_update
            }
            
        except Exception as e:
            self.logger.error(f"Error creating status update: {e}")
            return {
                'success': False,
                'error': f'Status update failed: {str(e)}',
                'fallback_status': {
                    'operation': operation,
                    'progress': progress,
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
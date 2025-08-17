"""
Custom Prompt Manager Service

Manages custom AI prompts for summarization and translation,
including validation, storage, and default prompt handling.
"""

from typing import Dict, Any, List, Optional
import re
import logging
from datetime import datetime

from .base import BaseService, PromptManagerInterface, ValidationError, ConfigurationError
from .models import CustomPromptConfiguration

logger = logging.getLogger(__name__)


class CustomPromptManager(BaseService, PromptManagerInterface):
    """Service for managing custom AI prompts"""
    
    # Default prompts for different AI operations
    DEFAULT_PROMPTS = {
        'summarization': """You are an expert meeting summarizer. Please analyze the following meeting transcript and provide a comprehensive summary.

Your summary should include:
1. Key discussion points and decisions made
2. Action items and their assigned owners
3. Important deadlines or next steps
4. Any unresolved issues or questions

Please format your response in a clear, structured manner that would be useful for someone who missed the meeting.

Meeting Transcript:
{transcript}

Please provide your summary:""",
        
        'translation': """You are a professional translator with expertise in multiple languages. Please translate the following text accurately while maintaining the original meaning, tone, and context.

Source text: {source_text}
Target language: {target_language}

Please provide a natural, fluent translation that preserves the original meaning and is appropriate for the context. If there are any cultural nuances or idiomatic expressions, please adapt them appropriately for the target language.

Translation:"""
    }
    
    # Required placeholders for each prompt type
    REQUIRED_PLACEHOLDERS = {
        'summarization': ['{transcript}'],
        'translation': ['{source_text}', '{target_language}']
    }
    
    def __init__(self, storage_backend: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Use provided storage backend or create in-memory storage
        self.storage = storage_backend or {}
        self.prompt_configurations = {}
    
    def validate_config(self) -> bool:
        """Validate service configuration"""
        return True  # Basic implementation always valid
    
    def save_custom_prompt(self, user_id: str, prompt_type: str, prompt_text: str) -> Dict[str, Any]:
        """
        Save custom prompt for user with comprehensive error handling
        
        Args:
            user_id: User identifier
            prompt_type: Type of prompt ('summarization' or 'translation')
            prompt_text: Custom prompt text
            
        Returns:
            Dictionary with save result and any errors/warnings
        """
        try:
            # Input validation
            if not user_id or not isinstance(user_id, str):
                return {
                    'success': False,
                    'error': 'Invalid user ID',
                    'error_code': 'INVALID_USER_ID',
                    'recovery_suggestions': ['Ensure you are properly logged in']
                }
            
            if not prompt_type or not isinstance(prompt_type, str):
                return {
                    'success': False,
                    'error': 'Invalid prompt type',
                    'error_code': 'INVALID_PROMPT_TYPE',
                    'recovery_suggestions': [f'Use one of: {", ".join(self.DEFAULT_PROMPTS.keys())}']
                }
            
            # Validate prompt type
            if prompt_type not in self.DEFAULT_PROMPTS:
                valid_types = ', '.join(self.DEFAULT_PROMPTS.keys())
                return {
                    'success': False,
                    'error': f'Invalid prompt type: {prompt_type}',
                    'error_code': 'UNSUPPORTED_PROMPT_TYPE',
                    'recovery_suggestions': [f'Use one of these prompt types: {valid_types}']
                }
            
            # Validate prompt text
            validation_result = self.validate_prompt(prompt_text, prompt_type)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': 'Prompt validation failed',
                    'error_code': 'VALIDATION_FAILED',
                    'validation_errors': validation_result['errors'],
                    'validation_warnings': validation_result.get('warnings', []),
                    'recovery_suggestions': validation_result.get('recovery_suggestions', [])
                }
            
            # Check for storage availability
            if not hasattr(self.storage, 'get') or not hasattr(self.storage, '__setitem__'):
                return {
                    'success': False,
                    'error': 'Storage backend not available',
                    'error_code': 'STORAGE_UNAVAILABLE',
                    'recovery_suggestions': [
                        'Storage system may be temporarily unavailable',
                        'Try saving again in a few moments',
                        'Contact support if the issue persists'
                    ]
                }
            
            # Create or update prompt configuration
            config_key = f"{user_id}_{prompt_type}"
            
            try:
                if config_key not in self.prompt_configurations:
                    self.prompt_configurations[config_key] = CustomPromptConfiguration(
                        user_id=user_id,
                        prompt_type=prompt_type
                    )
                
                config = self.prompt_configurations[config_key]
                config.set_custom_prompt(prompt_text)
                config.set_validation_result(True, [])
                
            except Exception as e:
                self.logger.error(f"Error creating prompt configuration: {e}")
                return {
                    'success': False,
                    'error': 'Failed to create prompt configuration',
                    'error_code': 'CONFIG_CREATION_FAILED',
                    'recovery_suggestions': [
                        'Try saving the prompt again',
                        'Check that your prompt is properly formatted',
                        'Contact support if the issue persists'
                    ]
                }
            
            # Store in backend storage with error handling
            try:
                if user_id not in self.storage:
                    self.storage[user_id] = {}
                
                if 'custom_prompts' not in self.storage[user_id]:
                    self.storage[user_id]['custom_prompts'] = {}
                
                # Create backup of existing prompt if it exists
                existing_prompt = self.storage[user_id]['custom_prompts'].get(prompt_type)
                
                self.storage[user_id]['custom_prompts'][prompt_type] = {
                    'custom_prompt': prompt_text,
                    'is_default': False,
                    'last_updated': config.updated_at,
                    'validation_status': 'valid',
                    'character_count': validation_result.get('character_count', len(prompt_text)),
                    'word_count': validation_result.get('word_count', len(prompt_text.split())),
                    'placeholder_count': validation_result.get('placeholder_count', 0)
                }
                
                # Verify the save was successful
                saved_prompt = self.storage[user_id]['custom_prompts'][prompt_type]
                if saved_prompt['custom_prompt'] != prompt_text:
                    # Restore backup if available
                    if existing_prompt:
                        self.storage[user_id]['custom_prompts'][prompt_type] = existing_prompt
                    
                    return {
                        'success': False,
                        'error': 'Prompt save verification failed',
                        'error_code': 'SAVE_VERIFICATION_FAILED',
                        'recovery_suggestions': [
                            'Try saving the prompt again',
                            'Check for any special characters that might be causing issues',
                            'Contact support if the issue persists'
                        ]
                    }
                
            except Exception as e:
                self.logger.error(f"Error storing prompt in backend: {e}")
                return {
                    'success': False,
                    'error': f'Failed to save prompt to storage: {str(e)}',
                    'error_code': 'STORAGE_SAVE_FAILED',
                    'recovery_suggestions': [
                        'Storage system may be temporarily unavailable',
                        'Try saving again in a few moments',
                        'Check that you have sufficient storage quota',
                        'Contact support if the issue persists'
                    ]
                }
            
            self.logger.info(f"Saved custom {prompt_type} prompt for user {user_id}")
            
            return {
                'success': True,
                'message': f'Custom {prompt_type} prompt saved successfully',
                'prompt_type': prompt_type,
                'character_count': validation_result.get('character_count', len(prompt_text)),
                'word_count': validation_result.get('word_count', len(prompt_text.split())),
                'validation_warnings': validation_result.get('warnings', []),
                'last_updated': config.updated_at
            }
            
        except ValidationError as e:
            self.logger.error(f"Validation error saving custom prompt: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'VALIDATION_ERROR',
                'recovery_suggestions': getattr(e, 'recovery_suggestions', [
                    'Check that your prompt meets all requirements',
                    'Ensure required placeholders are included',
                    'Try using the default prompt as a starting point'
                ])
            }
            
        except Exception as e:
            self.logger.error(f"Unexpected error saving custom prompt: {e}")
            return {
                'success': False,
                'error': f'An unexpected error occurred: {str(e)}',
                'error_code': 'UNEXPECTED_ERROR',
                'recovery_suggestions': [
                    'Try saving the prompt again',
                    'Check your internet connection',
                    'Try refreshing the page and saving again',
                    'Contact support if the issue persists'
                ]
            }
    
    def get_prompt(self, user_id: str, prompt_type: str) -> str:
        """
        Get custom or default prompt for user
        
        Args:
            user_id: User identifier
            prompt_type: Type of prompt ('summarization' or 'translation')
            
        Returns:
            Prompt text (custom if available, otherwise default)
        """
        try:
            # Validate prompt type
            if prompt_type not in self.DEFAULT_PROMPTS:
                self.logger.warning(f"Invalid prompt type requested: {prompt_type}")
                return self.DEFAULT_PROMPTS.get('summarization', '')
            
            # Check for custom prompt in configurations
            config_key = f"{user_id}_{prompt_type}"
            if config_key in self.prompt_configurations:
                config = self.prompt_configurations[config_key]
                if not config.is_default and config.custom_prompt:
                    return config.custom_prompt
            
            # Check storage backend
            if hasattr(self.storage, 'get'):
                user_data = self.storage.get(user_id, {})
                custom_prompts = user_data.get('custom_prompts', {})
                prompt_data = custom_prompts.get(prompt_type, {})
                
                if not prompt_data.get('is_default', True) and prompt_data.get('custom_prompt'):
                    return prompt_data['custom_prompt']
            
            # Return default prompt
            return self.DEFAULT_PROMPTS[prompt_type]
            
        except Exception as e:
            self.logger.error(f"Error getting prompt: {e}")
            return self.DEFAULT_PROMPTS.get(prompt_type, '')
    
    def reset_to_default(self, user_id: str, prompt_type: str) -> bool:
        """
        Reset prompt to default for user
        
        Args:
            user_id: User identifier
            prompt_type: Type of prompt ('summarization' or 'translation')
            
        Returns:
            True if reset successfully, False otherwise
        """
        try:
            # Validate prompt type
            if prompt_type not in self.DEFAULT_PROMPTS:
                raise ValidationError(f"Invalid prompt type: {prompt_type}")
            
            # Reset in configurations
            config_key = f"{user_id}_{prompt_type}"
            if config_key in self.prompt_configurations:
                config = self.prompt_configurations[config_key]
                config.reset_to_default()
            
            # Reset in storage backend
            if hasattr(self.storage, 'get') and hasattr(self.storage, '__setitem__'):
                if user_id in self.storage:
                    user_data = self.storage[user_id]
                    if 'custom_prompts' in user_data:
                        if prompt_type in user_data['custom_prompts']:
                            user_data['custom_prompts'][prompt_type] = {
                                'custom_prompt': None,
                                'is_default': True,
                                'last_updated': CustomPromptConfiguration(user_id, prompt_type).updated_at,
                                'validation_status': 'valid'
                            }
            
            self.logger.info(f"Reset {prompt_type} prompt to default for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error resetting prompt to default: {e}")
            return False
    
    def validate_prompt(self, prompt_text: str, prompt_type: str) -> Dict[str, Any]:
        """
        Validate prompt with comprehensive error checking and user-friendly messages
        
        Args:
            prompt_text: Prompt text to validate
            prompt_type: Type of prompt ('summarization' or 'translation')
            
        Returns:
            Dictionary with validation results and recovery suggestions
        """
        try:
            errors = []
            warnings = []
            recovery_suggestions = []
            
            # Input sanitization
            if prompt_text is None:
                errors.append("Prompt text cannot be empty")
                recovery_suggestions.append("Please enter a prompt text")
                return {
                    'is_valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'recovery_suggestions': recovery_suggestions
                }
            
            # Convert to string and strip whitespace
            prompt_text = str(prompt_text).strip()
            
            # Check if prompt type is valid
            if prompt_type not in self.REQUIRED_PLACEHOLDERS:
                valid_types = ', '.join(self.REQUIRED_PLACEHOLDERS.keys())
                errors.append(f"Invalid prompt type '{prompt_type}'. Valid types: {valid_types}")
                recovery_suggestions.append(f"Use one of these prompt types: {valid_types}")
                return {
                    'is_valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'recovery_suggestions': recovery_suggestions
                }
            
            # Check prompt length constraints
            if len(prompt_text) == 0:
                errors.append("Prompt cannot be empty")
                recovery_suggestions.extend([
                    "Enter a prompt that describes how you want the AI to process your content",
                    f"You can start with the default {prompt_type} prompt and modify it"
                ])
                return {
                    'is_valid': False,
                    'errors': errors,
                    'warnings': warnings,
                    'recovery_suggestions': recovery_suggestions
                }
            
            if len(prompt_text) < 10:
                errors.append("Prompt is too short (minimum 10 characters)")
                recovery_suggestions.extend([
                    "Add more detail to your prompt to help the AI understand what you want",
                    "Include instructions about the format or style you prefer"
                ])
            
            if len(prompt_text) > 5000:
                warnings.append("Prompt is very long (over 5000 characters) - this may affect performance")
                recovery_suggestions.append("Consider shortening your prompt while keeping the essential instructions")
            
            # Check for required placeholders
            required_placeholders = self.REQUIRED_PLACEHOLDERS[prompt_type]
            missing_placeholders = []
            
            for placeholder in required_placeholders:
                if placeholder not in prompt_text:
                    missing_placeholders.append(placeholder)
            
            if missing_placeholders:
                missing_str = ', '.join(missing_placeholders)
                errors.append(f"Missing required placeholders: {missing_str}")
                
                # Provide specific guidance based on prompt type
                if prompt_type == 'summarization':
                    recovery_suggestions.extend([
                        "Include {transcript} in your prompt where you want the meeting transcript to be inserted",
                        "Example: 'Please summarize this meeting transcript: {transcript}'"
                    ])
                elif prompt_type == 'translation':
                    recovery_suggestions.extend([
                        "Include {source_text} where the text to translate should be inserted",
                        "Include {target_language} where the target language should be specified",
                        "Example: 'Translate this text to {target_language}: {source_text}'"
                    ])
            
            # Check for security issues
            security_patterns = [
                (r'<script[^>]*>', "HTML script tags are not allowed"),
                (r'javascript:', "JavaScript URLs are not allowed"),
                (r'data:.*base64', "Base64 data URLs are not allowed"),
                (r'eval\s*\(', "JavaScript eval() function is not allowed"),
                (r'exec\s*\(', "Python exec() function is not allowed"),
                (r'import\s+os|from\s+os\s+import', "OS module imports are not allowed"),
                (r'__import__', "Dynamic imports are not allowed")
            ]
            
            for pattern, message in security_patterns:
                if re.search(pattern, prompt_text, re.IGNORECASE):
                    errors.append(f"Security issue: {message}")
                    recovery_suggestions.append("Remove potentially unsafe code or scripts from your prompt")
            
            # Check for balanced braces and proper placeholder formatting
            open_braces = prompt_text.count('{')
            close_braces = prompt_text.count('}')
            
            if open_braces != close_braces:
                warnings.append("Unbalanced braces detected - this might cause formatting issues")
                recovery_suggestions.append("Check that every opening brace '{' has a matching closing brace '}'")
            
            # Check for malformed placeholders
            malformed_placeholders = re.findall(r'\{[^}]*\{|\}[^{]*\}', prompt_text)
            if malformed_placeholders:
                warnings.append("Potentially malformed placeholders detected")
                recovery_suggestions.append("Check placeholder formatting - they should be like {placeholder_name}")
            
            # Check for common placeholder mistakes
            found_placeholders = self._extract_placeholders(prompt_text)
            suspicious_placeholders = []
            
            for placeholder in found_placeholders:
                # Check for spaces in placeholders
                if ' ' in placeholder:
                    suspicious_placeholders.append(placeholder)
                # Check for very long placeholder names
                elif len(placeholder) > 50:
                    suspicious_placeholders.append(placeholder)
            
            if suspicious_placeholders:
                warnings.append(f"Suspicious placeholders found: {', '.join(suspicious_placeholders[:3])}")
                recovery_suggestions.append("Placeholder names should be simple and without spaces")
            
            # Check for encoding issues
            try:
                prompt_text.encode('utf-8')
            except UnicodeEncodeError:
                errors.append("Prompt contains invalid characters")
                recovery_suggestions.append("Remove or replace any special characters that may be causing encoding issues")
            
            # Check for excessive repetition (potential copy-paste errors)
            words = prompt_text.lower().split()
            if len(words) > 10:
                word_counts = {}
                for word in words:
                    if len(word) > 3:  # Only check words longer than 3 characters
                        word_counts[word] = word_counts.get(word, 0) + 1
                
                repeated_words = [word for word, count in word_counts.items() if count > len(words) * 0.1]
                if repeated_words:
                    warnings.append("Excessive word repetition detected - this might be unintentional")
                    recovery_suggestions.append("Review your prompt for accidentally repeated text")
            
            # Check for proper instruction format
            if prompt_type == 'summarization':
                if 'summary' not in prompt_text.lower() and 'summarize' not in prompt_text.lower():
                    warnings.append("Prompt doesn't explicitly mention summarization")
                    recovery_suggestions.append("Consider including words like 'summarize' or 'summary' to make your intent clear")
            
            elif prompt_type == 'translation':
                if 'translate' not in prompt_text.lower() and 'translation' not in prompt_text.lower():
                    warnings.append("Prompt doesn't explicitly mention translation")
                    recovery_suggestions.append("Consider including words like 'translate' or 'translation' to make your intent clear")
            
            # Final validation
            is_valid = len(errors) == 0
            
            # Add success suggestions if valid
            if is_valid and not warnings:
                recovery_suggestions.append("Your prompt looks good! You can save it and start using it.")
            elif is_valid and warnings:
                recovery_suggestions.append("Your prompt is valid but has some warnings. You can save it as-is or address the warnings first.")
            
            return {
                'is_valid': is_valid,
                'errors': errors,
                'warnings': warnings,
                'recovery_suggestions': recovery_suggestions,
                'required_placeholders': required_placeholders,
                'found_placeholders': found_placeholders,
                'placeholder_count': len(found_placeholders),
                'character_count': len(prompt_text),
                'word_count': len(prompt_text.split()),
                'validation_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error validating prompt: {e}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'recovery_suggestions': [
                    "There was an error validating your prompt",
                    "Try simplifying your prompt and removing any special characters",
                    "Contact support if the issue persists"
                ],
                'validation_timestamp': datetime.utcnow().isoformat()
            }
    
    def get_default_prompt(self, prompt_type: str) -> str:
        """Get default prompt for a given type"""
        return self.DEFAULT_PROMPTS.get(prompt_type, '')
    
    def get_user_prompt_status(self, user_id: str) -> Dict[str, Any]:
        """Get status of all prompts for a user"""
        status = {}
        
        for prompt_type in self.DEFAULT_PROMPTS.keys():
            config_key = f"{user_id}_{prompt_type}"
            is_custom = False
            last_updated = None
            validation_status = 'valid'
            
            # Check configurations
            if config_key in self.prompt_configurations:
                config = self.prompt_configurations[config_key]
                is_custom = not config.is_default
                last_updated = config.updated_at
                validation_status = config.validation_status or 'valid'
            
            # Check storage backend
            elif hasattr(self.storage, 'get'):
                user_data = self.storage.get(user_id, {})
                custom_prompts = user_data.get('custom_prompts', {})
                prompt_data = custom_prompts.get(prompt_type, {})
                is_custom = not prompt_data.get('is_default', True)
                last_updated = prompt_data.get('last_updated')
                validation_status = prompt_data.get('validation_status', 'valid')
            
            status[prompt_type] = {
                'is_custom': is_custom,
                'is_default': not is_custom,
                'last_updated': last_updated,
                'validation_status': validation_status
            }
        
        return status
    
    def _extract_placeholders(self, prompt_text: str) -> List[str]:
        """Extract all placeholders from prompt text"""
        placeholder_pattern = r'\{([^}]+)\}'
        matches = re.findall(placeholder_pattern, prompt_text)
        return [f"{{{match}}}" for match in matches]
    
    def apply_prompt_template(self, user_id: str, prompt_type: str, **kwargs) -> str:
        """
        Apply template variables to a prompt
        
        Args:
            user_id: User identifier
            prompt_type: Type of prompt
            **kwargs: Template variables to substitute
            
        Returns:
            Formatted prompt with variables substituted
        """
        try:
            prompt_template = self.get_prompt(user_id, prompt_type)
            
            # Substitute template variables
            formatted_prompt = prompt_template.format(**kwargs)
            
            return formatted_prompt
            
        except KeyError as e:
            self.logger.error(f"Missing template variable: {e}")
            raise ValidationError(f"Missing required template variable: {e}")
        except Exception as e:
            self.logger.error(f"Error applying prompt template: {e}")
            raise ProcessingError(f"Failed to apply prompt template: {str(e)}")
    
    def export_user_prompts(self, user_id: str) -> Dict[str, Any]:
        """
        Export all custom prompts for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing user's custom prompt configuration
        """
        try:
            export_data = {
                'user_id': user_id,
                'export_timestamp': datetime.utcnow().isoformat(),
                'prompts': {},
                'prompt_status': self.get_user_prompt_status(user_id)
            }
            
            # Export each prompt type
            for prompt_type in self.DEFAULT_PROMPTS.keys():
                prompt_data = {
                    'prompt_type': prompt_type,
                    'is_custom': False,
                    'current_prompt': self.get_prompt(user_id, prompt_type),
                    'default_prompt': self.DEFAULT_PROMPTS[prompt_type],
                    'validation_result': None
                }
                
                # Check if user has custom prompt
                config_key = f"{user_id}_{prompt_type}"
                if config_key in self.prompt_configurations:
                    config = self.prompt_configurations[config_key]
                    prompt_data.update({
                        'is_custom': not config.is_default,
                        'custom_prompt': config.custom_prompt if not config.is_default else None,
                        'last_updated': config.updated_at,
                        'validation_result': {
                            'is_valid': config.validation_status == 'valid',
                            'status': config.validation_status
                        }
                    })
                
                # Check storage backend for additional info
                elif hasattr(self.storage, 'get'):
                    user_data = self.storage.get(user_id, {})
                    custom_prompts = user_data.get('custom_prompts', {})
                    prompt_storage_data = custom_prompts.get(prompt_type, {})
                    
                    if not prompt_storage_data.get('is_default', True):
                        prompt_data.update({
                            'is_custom': True,
                            'custom_prompt': prompt_storage_data.get('custom_prompt'),
                            'last_updated': prompt_storage_data.get('last_updated'),
                            'validation_result': {
                                'is_valid': prompt_storage_data.get('validation_status') == 'valid',
                                'status': prompt_storage_data.get('validation_status', 'valid')
                            }
                        })
                
                export_data['prompts'][prompt_type] = prompt_data
            
            self.logger.info(f"Exported custom prompts for user {user_id}")
            return export_data
            
        except Exception as e:
            self.logger.error(f"Error exporting user prompts: {e}")
            return {
                'user_id': user_id,
                'export_timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'prompts': {}
            }
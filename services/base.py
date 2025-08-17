"""
Base classes and interfaces for enhanced AI features services
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Base class for all enhanced AI services"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate service configuration"""
        pass
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default fallback"""
        return self.config.get(key, default)


class LanguageDetectionInterface(ABC):
    """Interface for language detection services"""
    
    @abstractmethod
    def process_language_detection(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process language detection from transcript data"""
        pass
    
    @abstractmethod
    def get_session_languages(self) -> List[Dict[str, Any]]:
        """Get all detected languages for current session"""
        pass
    
    @abstractmethod
    def get_language_timeline(self) -> List[Dict[str, Any]]:
        """Get timeline of language switches"""
        pass
    
    @abstractmethod
    def get_language_statistics(self) -> Dict[str, Any]:
        """Get language usage statistics"""
        pass


class PromptManagerInterface(ABC):
    """Interface for custom prompt management"""
    
    @abstractmethod
    def save_custom_prompt(self, user_id: str, prompt_type: str, prompt_text: str) -> bool:
        """Save custom prompt for user"""
        pass
    
    @abstractmethod
    def get_prompt(self, user_id: str, prompt_type: str) -> str:
        """Get custom or default prompt"""
        pass
    
    @abstractmethod
    def reset_to_default(self, user_id: str, prompt_type: str) -> bool:
        """Reset prompt to default"""
        pass
    
    @abstractmethod
    def validate_prompt(self, prompt_text: str, prompt_type: str) -> Dict[str, Any]:
        """Validate prompt contains required placeholders"""
        pass


class FileHandlerInterface(ABC):
    """Interface for file upload and processing"""
    
    @abstractmethod
    def validate_file(self, file_data: Any) -> Dict[str, Any]:
        """Validate uploaded file"""
        pass
    
    @abstractmethod
    def save_temp_file(self, file_data: Any) -> str:
        """Save file temporarily for processing"""
        pass
    
    @abstractmethod
    def cleanup_temp_file(self, file_path: str) -> bool:
        """Clean up temporary files"""
        pass


class EnhancedAssemblyAIInterface(ABC):
    """Interface for enhanced AssemblyAI functionality"""
    
    @abstractmethod
    def upload_audio_file(self, file_path: str) -> Dict[str, Any]:
        """Upload audio file to AssemblyAI"""
        pass
    
    @abstractmethod
    def transcribe_file(self, audio_url: str, **kwargs) -> Dict[str, Any]:
        """Transcribe uploaded file with enhanced features"""
        pass
    
    @abstractmethod
    def get_transcription_status(self, transcript_id: str) -> Dict[str, Any]:
        """Poll transcription status"""
        pass
    
    @abstractmethod
    def update_streaming_config(self, model: str) -> bool:
        """Update streaming configuration with selected model"""
        pass


class DataModel:
    """Base data model class with common functionality"""
    
    def __init__(self, **kwargs):
        self.created_at = kwargs.get('created_at', datetime.utcnow().isoformat())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def update(self, **kwargs):
        """Update model attributes"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow().isoformat()


class ServiceError(Exception):
    """Base exception for service errors"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ValidationError(ServiceError):
    """Exception for validation errors"""
    pass


class ConfigurationError(ServiceError):
    """Exception for configuration errors"""
    pass


class ProcessingError(ServiceError):
    """Exception for processing errors"""
    pass
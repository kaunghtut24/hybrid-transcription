"""
Enhanced AI Features Services Package

This package contains the core services for the enhanced AI features including:
- Language detection service
- Custom prompt management
- Enhanced AssemblyAI integration
- File upload handling
"""

from .base import (
    BaseService,
    LanguageDetectionInterface,
    PromptManagerInterface,
    FileHandlerInterface,
    EnhancedAssemblyAIInterface,
    DataModel,
    ServiceError,
    ValidationError,
    ConfigurationError,
    ProcessingError
)

from .models import (
    LanguageDetectionEvent,
    CustomPromptConfiguration,
    FileUploadSession,
    AssemblyAIModelConfiguration,
    SessionLanguageStatistics
)

from .language_detection import LanguageDetectionService
from .prompt_manager import CustomPromptManager

__version__ = "1.0.0"

__all__ = [
    # Base classes and interfaces
    'BaseService',
    'LanguageDetectionInterface',
    'PromptManagerInterface', 
    'FileHandlerInterface',
    'EnhancedAssemblyAIInterface',
    'DataModel',
    
    # Exceptions
    'ServiceError',
    'ValidationError',
    'ConfigurationError',
    'ProcessingError',
    
    # Data models
    'LanguageDetectionEvent',
    'CustomPromptConfiguration',
    'FileUploadSession',
    'AssemblyAIModelConfiguration',
    'SessionLanguageStatistics',
    
    # Services
    'LanguageDetectionService',
    'CustomPromptManager'
]
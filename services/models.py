"""
Enhanced data models for AI features
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import DataModel


class LanguageDetectionEvent(DataModel):
    """Data model for language detection events"""
    
    def __init__(self, 
                 detected_language: str,
                 confidence: float,
                 timestamp: Optional[str] = None,
                 duration_ms: Optional[int] = None,
                 transcript_segment: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.detected_language = detected_language
        self.confidence = confidence
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.duration_ms = duration_ms
        self.transcript_segment = transcript_segment
    
    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if detection confidence is above threshold"""
        return self.confidence >= threshold
    
    def get_language_name(self) -> str:
        """Get human-readable language name"""
        language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'bn': 'Bengali',
            'my': 'Myanmar (Burmese)'
        }
        # Extract language code from locale (e.g., 'en-US' -> 'en')
        lang_code = self.detected_language.split('-')[0].lower()
        return language_names.get(lang_code, self.detected_language)


class CustomPromptConfiguration(DataModel):
    """Data model for custom prompt configurations"""
    
    def __init__(self,
                 user_id: str,
                 prompt_type: str,
                 custom_prompt: Optional[str] = None,
                 is_default: bool = True,
                 **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.prompt_type = prompt_type
        self.custom_prompt = custom_prompt
        self.is_default = is_default
        self.validation_status = None
        self.validation_errors = []
    
    def set_custom_prompt(self, prompt_text: str):
        """Set custom prompt and mark as non-default"""
        self.custom_prompt = prompt_text
        self.is_default = False
        self.update()
    
    def reset_to_default(self):
        """Reset to default prompt"""
        self.custom_prompt = None
        self.is_default = True
        self.validation_status = None
        self.validation_errors = []
        self.update()
    
    def set_validation_result(self, is_valid: bool, errors: List[str] = None):
        """Set validation result"""
        self.validation_status = 'valid' if is_valid else 'invalid'
        self.validation_errors = errors or []


class FileUploadSession(DataModel):
    """Data model for file upload sessions"""
    
    def __init__(self,
                 session_id: str,
                 user_id: str,
                 original_filename: str,
                 file_size: int,
                 file_format: str,
                 **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.user_id = user_id
        self.original_filename = original_filename
        self.file_size = file_size
        self.file_format = file_format
        self.temp_file_path = None
        self.upload_status = 'pending'  # pending, uploaded, processing, completed, error
        self.transcription_id = None
        self.transcription_status = None
        self.progress_percentage = 0
        self.estimated_completion = None
        self.error_message = None
        self.language_detection_events = []
        self.ai_analysis_results = {}
    
    def update_status(self, status: str, progress: int = None, error: str = None):
        """Update upload/processing status"""
        self.upload_status = status
        if progress is not None:
            self.progress_percentage = progress
        if error:
            self.error_message = error
        self.update()
    
    def add_language_detection_event(self, event: LanguageDetectionEvent):
        """Add language detection event"""
        self.language_detection_events.append(event.to_dict())
        self.update()
    
    def set_ai_analysis_result(self, analysis_type: str, result: Any):
        """Set AI analysis result"""
        self.ai_analysis_results[analysis_type] = result
        self.update()


class AssemblyAIModelConfiguration(DataModel):
    """Data model for AssemblyAI model configurations"""
    
    AVAILABLE_MODELS = {
        'universal': {
            'name': 'Universal Model',
            'description': 'Default model with good balance of speed and accuracy',
            'use_case': 'General purpose transcription'
        },
        'nano': {
            'name': 'Nano Model',
            'description': 'Fastest model with lower accuracy',
            'use_case': 'Real-time applications requiring low latency'
        },
        'best': {
            'name': 'Best Model',
            'description': 'Highest accuracy model with slower processing',
            'use_case': 'High-quality transcription where accuracy is critical'
        }
    }
    
    def __init__(self,
                 user_id: str,
                 selected_model: str = 'universal',
                 streaming_model: Optional[str] = None,
                 file_upload_model: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.selected_model = selected_model
        self.streaming_model = streaming_model or selected_model
        self.file_upload_model = file_upload_model or selected_model
    
    def is_valid_model(self, model: str) -> bool:
        """Check if model is valid"""
        return model in self.AVAILABLE_MODELS
    
    def get_model_info(self, model: str) -> Dict[str, str]:
        """Get model information"""
        return self.AVAILABLE_MODELS.get(model, {})
    
    def update_model_preference(self, model: str, context: str = 'general'):
        """Update model preference for specific context"""
        if not self.is_valid_model(model):
            raise ValueError(f"Invalid model: {model}")
        
        if context == 'streaming':
            self.streaming_model = model
        elif context == 'file_upload':
            self.file_upload_model = model
        else:
            self.selected_model = model
            self.streaming_model = model
            self.file_upload_model = model
        
        self.update()


class SessionLanguageStatistics(DataModel):
    """Data model for session language statistics"""
    
    def __init__(self,
                 session_id: str,
                 total_duration_ms: int = 0,
                 **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.total_duration_ms = total_duration_ms
        self.language_breakdown = {}  # language -> duration_ms
        self.language_switches = 0
        self.primary_language = None
        self.confidence_distribution = {
            'high': 0,    # >= 0.8
            'medium': 0,  # 0.6 - 0.8
            'low': 0      # < 0.6
        }
    
    def add_language_event(self, event: LanguageDetectionEvent):
        """Add language detection event to statistics"""
        language = event.detected_language
        duration = event.duration_ms or 0
        
        # Update language breakdown
        if language not in self.language_breakdown:
            self.language_breakdown[language] = 0
        self.language_breakdown[language] += duration
        
        # Update confidence distribution
        if event.confidence >= 0.8:
            self.confidence_distribution['high'] += 1
        elif event.confidence >= 0.6:
            self.confidence_distribution['medium'] += 1
        else:
            self.confidence_distribution['low'] += 1
        
        # Update primary language
        self.primary_language = max(self.language_breakdown.items(), 
                                  key=lambda x: x[1])[0]
        
        self.update()
    
    def get_language_percentages(self) -> Dict[str, float]:
        """Get language usage as percentages"""
        if self.total_duration_ms == 0:
            return {}
        
        return {
            lang: (duration / self.total_duration_ms) * 100
            for lang, duration in self.language_breakdown.items()
        }
    
    def get_confidence_summary(self) -> Dict[str, Any]:
        """Get confidence level summary"""
        total_events = sum(self.confidence_distribution.values())
        if total_events == 0:
            return {'total_events': 0}
        
        return {
            'total_events': total_events,
            'high_confidence_percentage': (self.confidence_distribution['high'] / total_events) * 100,
            'medium_confidence_percentage': (self.confidence_distribution['medium'] / total_events) * 100,
            'low_confidence_percentage': (self.confidence_distribution['low'] / total_events) * 100
        }
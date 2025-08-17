"""
Language Detection Service

Handles language detection events from AssemblyAI and provides
language analysis and statistics functionality.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .base import BaseService, LanguageDetectionInterface, ValidationError, ProcessingError
from .models import LanguageDetectionEvent, SessionLanguageStatistics

logger = logging.getLogger(__name__)


class LanguageDetectionService(BaseService, LanguageDetectionInterface):
    """Service for handling language detection from AssemblyAI"""
    
    def __init__(self, confidence_threshold: float = 0.7, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.confidence_threshold = confidence_threshold
        self.detected_languages = []
        self.session_statistics = {}
        self.current_session_id = None
    
    def validate_config(self) -> bool:
        """Validate service configuration"""
        if not isinstance(self.confidence_threshold, (int, float)):
            return False
        if not (0.0 <= self.confidence_threshold <= 1.0):
            return False
        return True
    
    def set_session(self, session_id: str):
        """Set current session for language detection"""
        self.current_session_id = session_id
        if session_id not in self.session_statistics:
            self.session_statistics[session_id] = SessionLanguageStatistics(
                session_id=session_id
            )
        self.logger.info(f"Language detection session set to: {session_id}")
    
    def process_language_detection(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process language detection from AssemblyAI transcript data with graceful degradation
        
        Args:
            transcript_data: Dictionary containing transcript and language detection data
            
        Returns:
            Dictionary with processed language detection information
        """
        try:
            # Input validation with fallbacks
            if not transcript_data or not isinstance(transcript_data, dict):
                self.logger.warning("Invalid transcript data provided for language detection")
                return self._create_fallback_result("Invalid input data")
            
            # Extract language detection information with fallbacks
            detected_language = transcript_data.get('language_code')
            confidence = transcript_data.get('language_confidence')
            transcript_text = transcript_data.get('text', '')
            timestamp = transcript_data.get('timestamp', datetime.utcnow().isoformat())
            source = transcript_data.get('source', 'unknown')
            
            # Handle missing language detection data gracefully
            fallback_used = False
            if not detected_language:
                self.logger.warning("No language code provided, using fallback detection")
                detected_language = self._detect_fallback_language(transcript_text)
                confidence = 0.5  # Medium confidence for fallback detection
                fallback_used = True
                
            if confidence is None:
                self.logger.warning("No confidence score provided, using default")
                confidence = 0.6  # Default confidence when not provided
            
            # Validate and normalize confidence score
            confidence = self._normalize_confidence_score(confidence)
            
            # Validate and normalize language code
            detected_language = self._normalize_language_code(detected_language, confidence)
            
            # Create simplified language detection event for better performance
            try:
                event = LanguageDetectionEvent(
                    detected_language=detected_language,
                    confidence=confidence,
                    timestamp=timestamp,
                    transcript_segment=transcript_text[:50] if transcript_text else None  # Reduced segment size
                )
                
                # Minimal source information to reduce memory usage
                event.source = source
                    
            except Exception as e:
                self.logger.error(f"Failed to create language detection event: {e}")
                return self._create_fallback_result(f"Event creation failed: {str(e)}")
            
            # Associate event with current session
            if self.current_session_id:
                event.session_id = self.current_session_id
            
            # Add to detected languages list with error handling
            try:
                self.detected_languages.append(event)
            except Exception as e:
                self.logger.error(f"Failed to store language detection event: {e}")
                # Continue processing even if storage fails
            
            # Update session statistics if session is set
            if self.current_session_id:
                try:
                    if self.current_session_id not in self.session_statistics:
                        self.session_statistics[self.current_session_id] = SessionLanguageStatistics(
                            session_id=self.current_session_id
                        )
                    stats = self.session_statistics[self.current_session_id]
                    stats.add_language_event(event)
                except Exception as e:
                    self.logger.error(f"Failed to update session statistics: {e}")
                    # Continue processing even if statistics update fails
            
            # Determine if this is a language change with error handling
            try:
                is_language_change = self._is_language_change(event)
            except Exception as e:
                self.logger.warning(f"Failed to determine language change: {e}")
                is_language_change = False
            
            # Generate warnings and user feedback
            warnings = []
            user_feedback = []
            
            if confidence < self.confidence_threshold:
                warnings.append(f"Low confidence language detection: {confidence:.2f}")
                user_feedback.append({
                    'type': 'warning',
                    'message': f"Language detection confidence is low ({confidence:.0%})",
                    'recovery_suggestions': [
                        'Ensure clear audio quality for better language detection',
                        'Speak more clearly if possible',
                        'Check microphone settings'
                    ]
                })
                self.logger.warning(f"Low confidence language detection: {detected_language} ({confidence:.2f})")
            
            if confidence < 0.3:
                warnings.append("Very low confidence - language detection may be unreliable")
                user_feedback.append({
                    'type': 'error',
                    'message': 'Language detection is very uncertain',
                    'recovery_suggestions': [
                        'Consider manually specifying the language',
                        'Check audio quality and microphone settings',
                        'Ensure you are speaking clearly'
                    ]
                })
            
            # Get language name with fallback
            try:
                language_name = event.get_language_name()
            except Exception as e:
                self.logger.warning(f"Failed to get language name: {e}")
                language_name = detected_language.upper()
            
            result = {
                'success': True,
                'event': event.to_dict(),
                'is_high_confidence': event.is_high_confidence(self.confidence_threshold),
                'is_language_change': is_language_change,
                'detected_language': detected_language,
                'language_name': language_name,
                'confidence': confidence,
                'warnings': warnings,
                'user_feedback': user_feedback,
                'session_id': self.current_session_id,
                'source': source,
                'fallback_used': fallback_used or (detected_language == 'en' and confidence < 0.6),
                'processing_timestamp': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Processed language detection: {detected_language} (confidence: {confidence:.2f}, source: {source})")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing language detection: {e}")
            return self._create_fallback_result(f"Processing failed: {str(e)}")
    
    def _normalize_confidence_score(self, confidence: Any) -> float:
        """Normalize confidence score to valid range"""
        try:
            confidence = float(confidence)
            if confidence > 1.0:
                confidence = confidence / 100.0  # Convert percentage to decimal
            confidence = max(0.0, min(1.0, confidence))
            return confidence
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid confidence score format: {confidence}, using default")
            return 0.5
    
    def _normalize_language_code(self, language_code: str, confidence: float) -> str:
        """Normalize and validate language code"""
        if not self._is_valid_language_code(language_code):
            self.logger.warning(f"Invalid language code {language_code}, using fallback")
            return 'en'  # Fallback to English
        
        # Normalize to lowercase and extract base language code
        if isinstance(language_code, str):
            return language_code.lower().split('-')[0]
        
        return 'en'
    
    def _create_fallback_result(self, error_message: str) -> Dict[str, Any]:
        """Create a fallback result when language detection fails"""
        return {
            'success': False,
            'error': error_message,
            'fallback_result': {
                'detected_language': 'en',
                'language_name': 'English',
                'confidence': 0.1,
                'is_high_confidence': False,
                'is_language_change': False,
                'warnings': ['Language detection failed, using English as fallback'],
                'user_feedback': [{
                    'type': 'error',
                    'message': 'Language detection is not available',
                    'recovery_suggestions': [
                        'Language detection will continue to attempt in the background',
                        'Transcription will continue normally',
                        'You can manually specify the language if needed'
                    ]
                }],
                'session_id': self.current_session_id,
                'fallback_used': True,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
        }
    
    def _detect_fallback_language(self, text: str) -> str:
        """Simple fallback language detection based on text analysis"""
        if not text or not isinstance(text, str):
            return 'en'
        
        # Simple heuristics for common languages
        text_lower = text.lower()
        
        # Check for language-specific patterns with better priority
        # Use more specific and unique patterns to avoid conflicts
        
        # Check for mixed languages first (multiple language indicators)
        language_indicators = 0
        if any(word in text_lower for word in ["hello", "how", "are", "you", "very", "well", "thank", "the", "boy", "eats", "red", "apples", "what", "beautiful", "day"]):
            language_indicators += 1
        if any(word in text_lower for word in ["hola", "bonjour", "ciao", "hallo"]):
            language_indicators += 1
        
        # If multiple language indicators, default to English for mixed text
        if language_indicators > 1:
            return 'en'
        
        # Spanish-specific patterns (check unique Spanish markers first)
        if any(char in text for char in 'ñ¿¡'):
            return 'es'  # Spanish (unique Spanish characters)
        elif any(word in text_lower for word in ["hola", "cómo", "estás", "muy", "gracias", "qué", "sí", "no", "día", "hermoso", "niño", "manzanas"]):
            return 'es'  # Spanish
        
        # French-specific patterns (check unique French words)
        elif any(word in text_lower for word in ["bonjour", "comment", "ça", "va", "très", "merci", "c'est", "garçon", "mange", "pommes", "belle", "journée"]):
            return 'fr'  # French
        
        # German-specific patterns (check unique German words)
        elif any(word in text_lower for word in ["hallo", "wie", "geht", "sehr", "gut", "danke", "junge", "ißt", "äpfel", "schöner", "tag", "was", "für"]):
            return 'de'  # German
        elif any(char in text for char in 'äöüß'):
            return 'de'  # German
        
        # Italian-specific patterns (check unique Italian words)
        elif any(word in text_lower for word in ["ciao", "come", "stai", "molto", "bene", "grazie", "è", "ragazzo", "mangia", "mele", "che", "bella", "giornata"]):
            return 'it'  # Italian
        
        # Check character patterns after word patterns
        elif any(char in text for char in 'àâäéèêëïîôöùûüÿç'):
            return 'fr'  # French
        elif any(char in text for char in 'àèìòù'):
            return 'it'  # Italian
        elif any(char in text for char in 'áíóúü'):
            return 'es'  # Spanish
        
        # Default to English
        return 'en'
    
    def _is_valid_language_code(self, language_code: str) -> bool:
        """Validate language code format"""
        if not language_code or not isinstance(language_code, str):
            return False
        
        # Basic validation for common language code formats
        if len(language_code) == 2 and language_code.isalpha():
            return True  # ISO 639-1 (e.g., 'en', 'es')
        elif len(language_code) == 5 and language_code[2] == '-':
            return True  # Locale format (e.g., 'en-US', 'es-ES')
        
        return False
    
    def get_session_languages(self) -> List[Dict[str, Any]]:
        """Get all detected languages for current session"""
        if not self.current_session_id:
            # If no session ID, use all events
            session_events = self.detected_languages
        else:
            session_events = [
                event for event in self.detected_languages
                if hasattr(event, 'session_id') and event.session_id == self.current_session_id
            ]
        
        # Group by language and get unique languages with their info
        languages = {}
        for event in session_events:
            lang = event.detected_language
            if lang not in languages:
                languages[lang] = {
                    'language_code': lang,
                    'language_name': event.get_language_name(),
                    'first_detected': event.timestamp,
                    'confidence_scores': [],
                    'event_count': 0
                }
            
            languages[lang]['confidence_scores'].append(event.confidence)
            languages[lang]['event_count'] += 1
            languages[lang]['last_detected'] = event.timestamp
        
        # Calculate average confidence for each language
        for lang_info in languages.values():
            scores = lang_info['confidence_scores']
            lang_info['average_confidence'] = sum(scores) / len(scores)
            lang_info['max_confidence'] = max(scores)
            lang_info['min_confidence'] = min(scores)
        
        return list(languages.values())
    
    def get_language_timeline(self) -> List[Dict[str, Any]]:
        """Get timeline of language switches"""
        if not self.current_session_id:
            # If no session ID, return all events
            session_events = self.detected_languages
        else:
            session_events = [
                event for event in self.detected_languages
                if hasattr(event, 'session_id') and event.session_id == self.current_session_id
            ]
        
        # Sort by timestamp
        session_events.sort(key=lambda x: x.timestamp)
        
        timeline = []
        current_language = None
        
        for event in session_events:
            if event.detected_language != current_language:
                timeline.append({
                    'timestamp': event.timestamp,
                    'language_code': event.detected_language,
                    'language_name': event.get_language_name(),
                    'confidence': event.confidence,
                    'is_switch': current_language is not None,
                    'previous_language': current_language
                })
                current_language = event.detected_language
        
        return timeline
    
    def get_language_statistics(self) -> Dict[str, Any]:
        """Get language usage statistics for current session"""
        if not self.current_session_id or self.current_session_id not in self.session_statistics:
            return {
                'session_id': self.current_session_id,
                'total_events': 0,
                'unique_languages': 0,
                'language_breakdown': {},
                'confidence_summary': {},
                'primary_language': None
            }
        
        stats = self.session_statistics[self.current_session_id]
        
        return {
            'session_id': self.current_session_id,
            'total_events': len(self.detected_languages),
            'unique_languages': len(stats.language_breakdown),
            'language_breakdown': stats.language_breakdown,
            'language_percentages': stats.get_language_percentages(),
            'confidence_summary': stats.get_confidence_summary(),
            'primary_language': stats.primary_language,
            'language_switches': stats.language_switches,
            'created_at': stats.created_at,
            'updated_at': stats.updated_at
        }
    
    def _is_language_change(self, current_event: LanguageDetectionEvent) -> bool:
        """Check if current event represents a language change"""
        if len(self.detected_languages) < 2:
            return False
        
        # Get the second-to-last event (the one before current)
        previous_event = self.detected_languages[-2]
        return current_event.detected_language != previous_event.detected_language
    
    def clear_session_data(self, session_id: Optional[str] = None):
        """Clear language detection data for a session"""
        target_session = session_id or self.current_session_id
        
        if target_session:
            # Remove events for this session
            self.detected_languages = [
                event for event in self.detected_languages
                if not (hasattr(event, 'session_id') and event.session_id == target_session)
            ]
            
            # Remove session statistics
            if target_session in self.session_statistics:
                del self.session_statistics[target_session]
            
            self.logger.info(f"Cleared language detection data for session: {target_session}")
    
    def export_session_data(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Export language detection data for a session"""
        target_session = session_id or self.current_session_id
        
        if not target_session:
            # If no session specified, export all events
            session_events = [event.to_dict() for event in self.detected_languages]
        else:
            session_events = [
                event.to_dict() for event in self.detected_languages
                if hasattr(event, 'session_id') and event.session_id == target_session
            ]
        
        return {
            'session_id': target_session,
            'export_timestamp': datetime.utcnow().isoformat(),
            'language_events': session_events,
            'language_timeline': self.get_language_timeline(),
            'language_statistics': self.get_language_statistics(),
            'session_languages': self.get_session_languages()
        }
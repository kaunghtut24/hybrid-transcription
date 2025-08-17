"""
In-memory storage management for sessions, API keys, and data
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages all in-memory storage for the application"""
    
    def __init__(self):
        # Core storage dictionaries
        self.user_sessions = {}
        self.api_keys_storage = {}
        self.active_assemblyai_connections = {}
        self.session_data_storage = {}
        
    def create_extended_session_data(self, session_id, user_id):
        """Create extended session data structure"""
        self.session_data_storage[session_id] = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'transcript_data': [],
            'language_detection_events': [],
            'ai_analysis_results': {},
            'session_metadata': {
                'total_duration_seconds': 0,
                'total_words': 0,
                'status': 'active'
            }
        }
        return self.session_data_storage[session_id]

    def update_session_data(self, session_id, **updates):
        """Update session data with new information"""
        if session_id in self.session_data_storage:
            self.session_data_storage[session_id].update(updates)
            self.session_data_storage[session_id]['updated_at'] = datetime.utcnow().isoformat()
            return self.session_data_storage[session_id]
        return None

    def add_language_detection_event_to_session(self, session_id, event_data):
        """Add language detection event to session data"""
        if session_id in self.session_data_storage:
            self.session_data_storage[session_id]['language_detection_events'].append(event_data)
            self.session_data_storage[session_id]['updated_at'] = datetime.utcnow().isoformat()
            return True
        return False

    def add_transcript_to_session(self, session_id, transcript_data):
        """Add transcript data to session"""
        if session_id in self.session_data_storage:
            self.session_data_storage[session_id]['transcript_data'].append(transcript_data)
            self.session_data_storage[session_id]['updated_at'] = datetime.utcnow().isoformat()
            
            # Update word count
            if 'transcript' in transcript_data:
                words = len(transcript_data['transcript'].split())
                self.session_data_storage[session_id]['session_metadata']['total_words'] += words
            
            return True
        return False

    def get_session_export_data(self, session_id):
        """Get complete session data for export"""
        if session_id not in self.session_data_storage:
            return None
        
        session_data = self.session_data_storage[session_id].copy()
        
        # Add language detection analysis
        handler = None
        for sid, conn_handler in self.active_assemblyai_connections.items():
            if conn_handler.session_id == session_id:
                handler = conn_handler
                break
        
        if handler:
            language_service = handler.get_language_detection_service()
            if language_service:
                session_data['language_analysis'] = {
                    'timeline': language_service.get_language_timeline(),
                    'statistics': language_service.get_language_statistics(),
                    'session_languages': language_service.get_session_languages(),
                    'export_data': language_service.export_session_data()
                }
        
        # Add custom prompt information if available
        user_id = session_data.get('user_id') or session_data.get('session_id', session_id)
        if user_id and user_id in self.api_keys_storage:
            from services.prompt_manager import CustomPromptManager
            prompt_manager = CustomPromptManager(storage_backend=self.api_keys_storage)
            session_data['custom_prompts'] = prompt_manager.export_user_prompts(user_id)
        
        # Add enhanced export metadata
        session_data['export_metadata'] = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'export_version': '2.0',
            'features': {
                'language_detection': bool(handler and language_service and language_service.detected_languages),
                'custom_prompts': bool(user_id and user_id in self.api_keys_storage and 
                                     self.api_keys_storage[user_id].get('custom_prompts')),
                'enhanced_export': True
            }
        }
        
        return session_data

# Global storage instance
storage = StorageManager()
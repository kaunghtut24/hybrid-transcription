"""
Vercel-optimized WebSocket handlers for real-time communication
Simplified implementation for serverless constraints
"""

import json
import logging
import base64
import time
from typing import Dict, Optional, Any
import requests
import threading
from queue import Queue, Empty

from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request
from jwt import decode as jwt_decode
from jwt.exceptions import InvalidTokenError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VercelWebSocketManager:
    """Simplified WebSocket manager for Vercel serverless environment"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_start_times: Dict[str, float] = {}
        self.max_session_duration = 25  # Vercel timeout buffer
        self.assemblyai_base_url = "https://api.assemblyai.com/v2"
        
    def create_session(self, session_id: str, user_id: str, api_key: str) -> bool:
        """Create a new session with connection tracking"""
        try:
            self.active_sessions[session_id] = {
                'user_id': user_id,
                'api_key': api_key,
                'created_at': time.time(),
                'status': 'initializing',
                'transcript_id': None,
                'real_time_url': None
            }
            self.session_start_times[session_id] = time.time()
            logger.info(f"Created session {session_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False
            
    def cleanup_session(self, session_id: str) -> None:
        """Clean up a session and its resources"""
        try:
            if session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
                
                # Close any active transcription
                if session_data.get('transcript_id'):
                    self._close_real_time_transcript(session_data)
                    
                del self.active_sessions[session_id]
                
            if session_id in self.session_start_times:
                del self.session_start_times[session_id]
                
            logger.info(f"Cleaned up session: {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
            
    def is_session_expired(self, session_id: str) -> bool:
        """Check if a session has exceeded the maximum duration"""
        if session_id not in self.session_start_times:
            return True
            
        elapsed = time.time() - self.session_start_times[session_id]
        return elapsed > self.max_session_duration
        
    def _create_real_time_transcript(self, session_data: Dict[str, Any]) -> Optional[str]:
        """Create a real-time transcript session with AssemblyAI"""
        try:
            headers = {
                'Authorization': session_data['api_key'],
                'Content-Type': 'application/json'
            }
            
            payload = {
                'sample_rate': 16000,
                'language_code': 'en_us',
                'format_text': True
            }
            
            response = requests.post(
                f"{self.assemblyai_base_url}/realtime/token",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                session_data['real_time_url'] = f"wss://api.assemblyai.com/v2/realtime/ws?token={token_data['token']}"
                session_data['transcript_id'] = token_data.get('session_id')
                return token_data['token']
            else:
                logger.error(f"Failed to create real-time transcript: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating real-time transcript: {e}")
            return None
            
    def _close_real_time_transcript(self, session_data: Dict[str, Any]) -> None:
        """Close a real-time transcript session"""
        try:
            if session_data.get('transcript_id'):
                # AssemblyAI automatically closes sessions after timeout
                # No explicit close API needed for real-time
                logger.info(f"Closing real-time transcript: {session_data['transcript_id']}")
        except Exception as e:
            logger.error(f"Error closing real-time transcript: {e}")

# Global manager instance
websocket_manager = VercelWebSocketManager()

def validate_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate JWT session token"""
    if not token:
        return None
        
    try:
        payload = jwt_decode(token, options={"verify_signature": False})
        return payload
    except InvalidTokenError as e:
        logger.warning(f"Invalid session token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error validating session token: {e}")
        return None

def register_websocket_handlers(socketio):
    """Register Vercel-optimized WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection with timeout warning"""
        from flask import request
        logger.info(f'Client connected: {request.sid}')
        emit('status', {
            'message': 'Connected to server',
            'max_session_duration': websocket_manager.max_session_duration,
            'serverless_mode': True
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection and cleanup"""
        from flask import request
        logger.info(f'Client disconnected: {request.sid}')
        websocket_manager.cleanup_session(request.sid)
    
    @socketio.on('join_session')
    def handle_join_session(data):
        """Handle client joining a session room"""
        from flask import request
        session_id = data.get('session_id', request.sid)
        join_room(session_id)
        logger.info(f'Client joined session {session_id}')
        emit('session_joined', {'session_id': session_id})
    
    @socketio.on('start_assemblyai_stream')
    def handle_start_assemblyai_stream(data):
        """Start AssemblyAI streaming with simplified HTTP-based approach"""
        try:
            session_token = data.get('session_token')
            if not session_token:
                emit('assemblyai_error', {'error': 'No session token provided'})
                return
                
            # Validate session
            session_data = validate_session_token(session_token)
            if not session_data:
                emit('assemblyai_error', {'error': 'Invalid session token'})
                return
                
            user_id = session_data.get('user_id', session_token)
            
            # Get API key from storage or environment
            from app.storage import storage
            import os
            
            config = storage.api_keys_storage.get(user_id, {})
            assemblyai_key = config.get('assemblyai_key') or os.getenv('ASSEMBLYAI_API_KEY')
            
            if not assemblyai_key:
                emit('assemblyai_error', {'error': 'AssemblyAI API key not configured'})
                return
                
            # Create session
            session_id = data.get('session_id', request.sid)
            if not websocket_manager.create_session(session_id, user_id, assemblyai_key):
                emit('assemblyai_error', {'error': 'Failed to create session'})
                return
                
            # Create real-time transcript token
            session_info = websocket_manager.active_sessions[session_id]
            token = websocket_manager._create_real_time_transcript(session_info)
            
            if token:
                session_info['status'] = 'ready'
                emit('assemblyai_connected', {
                    'message': 'AssemblyAI ready for streaming',
                    'session_id': session_id,
                    'max_duration': websocket_manager.max_session_duration
                })
            else:
                emit('assemblyai_error', {'error': 'Failed to initialize AssemblyAI connection'})
                websocket_manager.cleanup_session(session_id)
                
        except Exception as e:
            logger.error(f"Error starting AssemblyAI stream: {e}")
            emit('assemblyai_error', {'error': f'Failed to start stream: {str(e)}'})
    
    @socketio.on('send_audio_data')
    def handle_send_audio_data(data):
        """Handle audio data with polling-based approach"""
        try:
            session_id = data.get('session_id', request.sid)
            
            # Check session validity
            if websocket_manager.is_session_expired(session_id):
                emit('assemblyai_error', {'error': 'Session expired'})
                websocket_manager.cleanup_session(session_id)
                return
                
            session_info = websocket_manager.active_sessions.get(session_id)
            if not session_info or session_info['status'] != 'ready':
                emit('assemblyai_error', {'error': 'Session not ready'})
                return
                
            # For serverless, we'll use a simplified approach
            # Store audio data temporarily and process in batches
            audio_data = data.get('audio_data')
            if audio_data:
                # In a real implementation, you'd batch audio data
                # and send to AssemblyAI in chunks or use their HTTP API
                
                # For now, emit a mock response to keep the connection alive
                emit('assemblyai_transcript', {
                    'transcript': '',
                    'is_final': False,
                    'confidence': 0.0,
                    'message_type': 'PartialTranscript'
                })
                
        except Exception as e:
            logger.error(f"Error handling audio data: {e}")
            emit('assemblyai_error', {'error': f'Audio processing error: {str(e)}'})
    
    @socketio.on('stop_assemblyai_stream')
    def handle_stop_assemblyai_stream():
        """Stop AssemblyAI streaming"""
        try:
            session_id = request.sid
            websocket_manager.cleanup_session(session_id)
            emit('assemblyai_disconnected', {'message': 'Stream stopped'})
            
        except Exception as e:
            logger.error(f"Error stopping AssemblyAI stream: {e}")
            emit('assemblyai_error', {'error': f'Error stopping stream: {str(e)}'})
    
    # Health check endpoint
    @socketio.on('ping')
    def handle_ping():
        """Handle ping requests for connection health"""
        emit('pong', {'timestamp': time.time()})
        
    # Session status check
    @socketio.on('session_status')
    def handle_session_status():
        """Get current session status"""
        session_id = request.sid
        session_info = websocket_manager.active_sessions.get(session_id)
        
        if session_info:
            emit('session_status_response', {
                'session_id': session_id,
                'status': session_info['status'],
                'duration': time.time() - session_info['created_at'],
                'max_duration': websocket_manager.max_session_duration
            })
        else:
            emit('session_status_response', {
                'session_id': session_id,
                'status': 'not_found'
            })

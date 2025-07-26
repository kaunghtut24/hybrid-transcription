#!/usr/bin/env python3
"""
AssemblyAI WebSocket Streaming Handler
Handles real-time audio streaming to AssemblyAI and forwards results to the frontend
"""

import json
import threading
import time
import websocket
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class AssemblyAIWebSocketHandler:
    def __init__(self, api_key, socketio_instance, session_id):
        self.api_key = api_key
        self.socketio = socketio_instance
        self.session_id = session_id
        self.ws_app = None
        self.ws_thread = None
        self.stop_event = threading.Event()
        self.is_connected = False
        
        # AssemblyAI Configuration
        self.connection_params = {
            "sample_rate": 16000,
            "format_turns": True,
        }
        
        self.api_endpoint_base_url = "wss://streaming.assemblyai.com/v3/ws"
        self.api_endpoint = f"{self.api_endpoint_base_url}?{urlencode(self.connection_params)}"
        
    def start_connection(self):
        """Start the WebSocket connection to AssemblyAI"""
        try:
            self.ws_app = websocket.WebSocketApp(
                self.api_endpoint,
                header={"Authorization": self.api_key},
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            
            # Run WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws_app.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            logger.info(f"AssemblyAI WebSocket connection started for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start AssemblyAI WebSocket: {e}")
            return False
    
    def send_audio_data(self, audio_data):
        """Send audio data to AssemblyAI"""
        if self.ws_app and self.is_connected:
            try:
                self.ws_app.send(audio_data, websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                logger.error(f"Error sending audio data: {e}")
    
    def stop_connection(self):
        """Stop the WebSocket connection"""
        self.stop_event.set()
        
        if self.ws_app and self.is_connected:
            try:
                # Send termination message
                terminate_message = {"type": "Terminate"}
                self.ws_app.send(json.dumps(terminate_message))
                time.sleep(0.5)  # Give time for message to be sent
            except Exception as e:
                logger.error(f"Error sending termination message: {e}")
            
            self.ws_app.close()
        
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2.0)
        
        logger.info(f"AssemblyAI WebSocket connection stopped for session {self.session_id}")
    
    def _on_open(self, ws):
        """Called when the WebSocket connection is established"""
        self.is_connected = True
        logger.info(f"AssemblyAI WebSocket opened for session {self.session_id}")
        
        # Notify frontend that connection is established
        self.socketio.emit('assemblyai_connected', {
            'status': 'connected',
            'message': 'Connected to AssemblyAI streaming'
        }, room=self.session_id)
    
    def _on_message(self, ws, message):
        """Handle messages from AssemblyAI"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == "Begin":
                session_id = data.get('id')
                expires_at = data.get('expires_at')
                logger.info(f"AssemblyAI session began: ID={session_id}")
                
                self.socketio.emit('assemblyai_session_begin', {
                    'session_id': session_id,
                    'expires_at': expires_at
                }, room=self.session_id)
                
            elif msg_type == "Turn":
                transcript = data.get('transcript', '')
                formatted = data.get('turn_is_formatted', False)
                confidence = data.get('confidence', 0.9)
                
                # Send transcript to frontend
                self.socketio.emit('assemblyai_transcript', {
                    'transcript': transcript,
                    'is_final': formatted,
                    'confidence': confidence
                }, room=self.session_id)
                
            elif msg_type == "Termination":
                audio_duration = data.get('audio_duration_seconds', 0)
                session_duration = data.get('session_duration_seconds', 0)
                logger.info(f"AssemblyAI session terminated: Audio={audio_duration}s, Session={session_duration}s")
                
                self.socketio.emit('assemblyai_session_end', {
                    'audio_duration': audio_duration,
                    'session_duration': session_duration
                }, room=self.session_id)
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding AssemblyAI message: {e}")
        except Exception as e:
            logger.error(f"Error handling AssemblyAI message: {e}")
    
    def _on_error(self, ws, error):
        """Called when a WebSocket error occurs"""
        logger.error(f"AssemblyAI WebSocket error for session {self.session_id}: {error}")
        
        self.socketio.emit('assemblyai_error', {
            'error': str(error)
        }, room=self.session_id)
        
        self.stop_event.set()
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Called when the WebSocket connection is closed"""
        self.is_connected = False

        # Log more detailed information about the close
        if close_status_code == 3005:
            logger.error(f"AssemblyAI WebSocket authentication failed for session {self.session_id}: Status={close_status_code}, Message={close_msg}")
            error_msg = "Authentication failed - please check your AssemblyAI API key"
        elif close_status_code == 3006:
            logger.error(f"AssemblyAI WebSocket rate limit exceeded for session {self.session_id}: Status={close_status_code}")
            error_msg = "Rate limit exceeded - too many concurrent connections"
        elif close_status_code == 3007:
            logger.error(f"AssemblyAI WebSocket insufficient credits for session {self.session_id}: Status={close_status_code}")
            error_msg = "Insufficient credits in your AssemblyAI account"
        else:
            logger.info(f"AssemblyAI WebSocket closed for session {self.session_id}: Status={close_status_code}, Message={close_msg}")
            error_msg = f"Connection closed: {close_msg}" if close_msg else "Connection closed"

        self.socketio.emit('assemblyai_disconnected', {
            'status_code': close_status_code,
            'message': error_msg,
            'raw_message': close_msg
        }, room=self.session_id)
"""
WebSocket event handlers
"""

from flask_socketio import emit, join_room, leave_room
from app.storage import storage
import logging
import websocket

logger = logging.getLogger(__name__)

def register_websocket_handlers(socketio):
    """Register all WebSocket event handlers"""
    
    # Store socketio instance for use in callbacks
    global socketio_instance
    socketio_instance = socketio
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info('Client connected to main namespace')
        emit('status', {'message': 'Connected to server'})
        emit('test_response', {'message': 'SocketIO is working'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info('Client disconnected')
    
    @socketio.on('join_session')
    def handle_join_session(data):
        """Handle client joining a session room"""
        session_id = data.get('session_id')
        if session_id:
            join_room(session_id)
            logger.info(f'Client joined session {session_id}')
            emit('session_joined', {'session_id': session_id})
    
    @socketio.on('leave_session')
    def handle_leave_session(data):
        """Handle client leaving a session room"""
        session_id = data.get('session_id')
        if session_id:
            leave_room(session_id)
            logger.info(f'Client left session {session_id}')
            emit('session_left', {'session_id': session_id})
    
    @socketio.on('transcript_update')
    def handle_transcript_update(data):
        """Handle transcript updates from clients"""
        session_id = data.get('session_id')
        transcript_data = data.get('transcript_data')
        
        if session_id and transcript_data:
            # Store transcript data
            storage.add_transcript_to_session(session_id, transcript_data)
            
            # Broadcast to all clients in the session
            emit('transcript_updated', {
                'session_id': session_id,
                'transcript_data': transcript_data
            }, room=session_id)
    
    @socketio.on('language_detection')
    def handle_language_detection(data):
        """Handle language detection events"""
        session_id = data.get('session_id')
        language_data = data.get('language_data')
        
        if session_id and language_data:
            # Store language detection event
            storage.add_language_detection_event_to_session(session_id, language_data)
            
            # Broadcast to all clients in the session
            emit('language_detected', {
                'session_id': session_id,
                'language_data': language_data
            }, room=session_id)
    
    # AssemblyAI WebSocket Proxy Namespace
    @socketio.on('connect', namespace='/assemblyai-streaming')
    def handle_assemblyai_connect(auth):
        """Handle AssemblyAI streaming connection with proper authentication"""
        import websocket
        import json
        import threading
        from urllib.parse import urlencode
        from flask import request
        
        logger.info('AssemblyAI streaming client connected')
        
        # Get user session and API key
        session_token = auth.get('token') if auth else None
        if not session_token:
            emit('error', {'message': 'No session token provided'}, namespace='/assemblyai-streaming')
            return False
        
        # Get user ID from session token
        try:
            import jwt
            payload = jwt.decode(session_token, options={"verify_signature": False})
            user_id = payload.get('user_id')
            logger.info(f'Decoded user_id: {user_id}')
        except Exception as e:
            logger.warning(f'JWT decode failed: {e}, using token as user_id')
            user_id = session_token  # Fallback
        
        # Get API key
        config = storage.api_keys_storage.get(user_id, {})
        assemblyai_key = config.get('assemblyai_key')
        if not assemblyai_key:
            import os
            assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
        
        logger.info(f'API key found: {bool(assemblyai_key)}')
        
        if not assemblyai_key:
            logger.error('No AssemblyAI API key found')
            emit('error', {'message': 'AssemblyAI API key not configured'}, namespace='/assemblyai-streaming')
            return False
        
        # Store connection info
        storage.active_assemblyai_connections[request.sid] = {
            'user_id': user_id,
            'api_key': assemblyai_key,
            'upstream_ws': None
        }
        
        logger.info(f'AssemblyAI proxy connection established for user {user_id}')
        emit('connected', {'message': 'Connected to AssemblyAI proxy'}, namespace='/assemblyai-streaming')
        return True
    
    @socketio.on('start_streaming', namespace='/assemblyai-streaming')
    def handle_start_streaming(data):
        """Start AssemblyAI streaming connection"""
        try:
            import websocket
            import json
            import threading
            from urllib.parse import urlencode
            from flask import request
            
            logger.info(f'Starting AssemblyAI streaming for session {request.sid}')
            
            connection_info = storage.active_assemblyai_connections.get(request.sid)
            if not connection_info:
                logger.error('No connection info found for session')
                emit('error', {'message': 'Not authenticated'}, namespace='/assemblyai-streaming')
                return
        except ImportError as e:
            logger.error(f'Missing required library: {e}')
            emit('error', {'message': f'Server configuration error: {e}'}, namespace='/assemblyai-streaming')
            return
        
        # Build AssemblyAI WebSocket URL with proper parameters
        connection_params = {
            'sample_rate': data.get('sample_rate', 16000),
            'format_turns': data.get('format_turns', True)
        }
        
        api_endpoint = f"wss://streaming.assemblyai.com/v3/ws?{urlencode(connection_params)}"
        
        # Store the current session ID for use in callbacks
        current_sid = request.sid
        
        def on_message(ws, message):
            """Forward messages from AssemblyAI to client"""
            try:
                import json
                data = json.loads(message)
                logger.info(f"Received AssemblyAI message: {data.get('type', 'unknown')} - {data}")
                # Use socketio instance directly to avoid context issues
                socketio_instance.emit('assemblyai_message', data, namespace='/assemblyai-streaming', room=current_sid)
            except Exception as e:
                logger.error(f"Error forwarding AssemblyAI message: {e}")
        
        def on_error(ws, error):
            """Handle AssemblyAI WebSocket errors"""
            logger.error(f"AssemblyAI WebSocket error: {error}")
            try:
                socketio_instance.emit('assemblyai_error', {'error': str(error)}, namespace='/assemblyai-streaming', room=current_sid)
            except Exception as e:
                logger.error(f"Error emitting AssemblyAI error: {e}")
        
        def on_close(ws, close_status_code, close_msg):
            """Handle AssemblyAI WebSocket close"""
            logger.info(f"AssemblyAI WebSocket closed: {close_status_code} {close_msg}")
            try:
                socketio_instance.emit('assemblyai_closed', {
                    'code': close_status_code, 
                    'message': close_msg
                }, namespace='/assemblyai-streaming', room=current_sid)
            except Exception as e:
                logger.error(f"Error emitting AssemblyAI close: {e}")
        
        def on_open(ws):
            """Handle AssemblyAI WebSocket open"""
            logger.info("AssemblyAI WebSocket connected via proxy")
            try:
                socketio_instance.emit('assemblyai_connected', {'message': 'Connected to AssemblyAI'}, namespace='/assemblyai-streaming', room=current_sid)
            except Exception as e:
                logger.error(f"Error emitting AssemblyAI connected: {e}")
        
        try:
            logger.info(f'Creating WebSocket connection to: {api_endpoint}')
            
            # Create WebSocket connection with proper Authorization header
            upstream_ws = websocket.WebSocketApp(
                api_endpoint,
                header={"Authorization": connection_info['api_key']},
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Store upstream WebSocket
            connection_info['upstream_ws'] = upstream_ws
            
            logger.info('Starting WebSocket thread')
            
            # Start WebSocket in a separate thread
            ws_thread = threading.Thread(target=upstream_ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            logger.info('WebSocket thread started successfully')
            
        except Exception as e:
            logger.error(f"Failed to create AssemblyAI WebSocket: {e}")
            emit('error', {'message': f'Failed to connect to AssemblyAI: {str(e)}'}, namespace='/assemblyai-streaming')
    
    @socketio.on('audio_data', namespace='/assemblyai-streaming')
    def handle_audio_data(data):
        """Forward audio data to AssemblyAI"""
        from flask import request
        
        connection_info = storage.active_assemblyai_connections.get(request.sid)
        if not connection_info or not connection_info.get('upstream_ws'):
            logger.warning(f"No connection info found for session {request.sid}")
            return
        
        upstream_ws = connection_info['upstream_ws']
        if upstream_ws.sock and upstream_ws.sock.connected:
            try:
                # Get audio data
                audio_data = data.get('audio')
                if audio_data:
                    # Log audio data reception (only first few times to avoid spam)
                    if not hasattr(handle_audio_data, 'log_count'):
                        handle_audio_data.log_count = 0
                    
                    if handle_audio_data.log_count < 5:
                        logger.info(f"Received audio data: {len(audio_data)} items (type: {type(audio_data)})")
                        handle_audio_data.log_count += 1
                    
                    # Convert array of bytes back to bytes object
                    if isinstance(audio_data, list):
                        audio_bytes = bytes(audio_data)
                    elif isinstance(audio_data, (bytes, bytearray)):
                        audio_bytes = audio_data
                    else:
                        logger.warning(f"Unexpected audio data type: {type(audio_data)}")
                        return
                    
                    # Log sample bytes for debugging
                    if handle_audio_data.log_count <= 5:
                        sample_bytes = audio_bytes[:min(10, len(audio_bytes))]
                        logger.info(f"Audio bytes sample: {[int(b) for b in sample_bytes]}")
                        logger.info(f"Forwarding {len(audio_bytes)} bytes to AssemblyAI")
                    
                    upstream_ws.send(audio_bytes, websocket.ABNF.OPCODE_BINARY)
                else:
                    logger.warning("Received audio_data event but no audio data found")
            except Exception as e:
                logger.error(f"Error forwarding audio data: {e}")
        else:
            logger.warning(f"Upstream WebSocket not connected for session {request.sid}")
    
    @socketio.on('disconnect', namespace='/assemblyai-streaming')
    def handle_assemblyai_disconnect():
        """Handle AssemblyAI streaming disconnection"""
        from flask import request
        import json
        
        connection_info = storage.active_assemblyai_connections.get(request.sid)
        if connection_info:
            upstream_ws = connection_info.get('upstream_ws')
            if upstream_ws:
                try:
                    # Send termination message
                    upstream_ws.send(json.dumps({"type": "Terminate"}))
                    upstream_ws.close()
                except Exception as e:
                    logger.error(f"Error closing AssemblyAI WebSocket: {e}")
            
            # Clean up connection info
            del storage.active_assemblyai_connections[request.sid]
        
        logger.info('AssemblyAI streaming client disconnected')
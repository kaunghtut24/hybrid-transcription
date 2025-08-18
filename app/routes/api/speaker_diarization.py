"""
Speaker Diarization API routes for advanced speaker identification
across multiple audio clips using AssemblyAI and NeMo TitaNet
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from app.auth import require_session
from app.storage import storage
import logging
import os
import asyncio
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)
speaker_diarization_api = Blueprint('speaker_diarization_api', __name__)

# Store active speaker diarization sessions
active_diarization_sessions = {}

@speaker_diarization_api.route('/info', methods=['GET'])
def get_speaker_diarization_info():
    """Get information about speaker diarization capabilities - no auth required"""
    try:
        # Try to import the service to check availability
        from services.speaker_diarization import create_speaker_diarization_service
        
        # Check for required dependencies
        dependencies = {
            'pydub': False,
            'numpy': False,
            'nemo_toolkit': False
        }
        
        try:
            import pydub
            dependencies['pydub'] = True
        except ImportError:
            pass
            
        try:
            import numpy
            dependencies['numpy'] = True
        except ImportError:
            pass
            
        try:
            import nemo.collections.asr
            dependencies['nemo_toolkit'] = True
        except ImportError:
            pass
        
        return jsonify({
            'available': True,
            'version': '1.0.0',
            'description': 'Advanced speaker diarization with cross-clip speaker identification',
            'features': [
                'Multi-clip speaker identification',
                'Speaker voice embedding comparison using NeMo TitaNet',
                'Unified speaker labeling across audio chunks',
                'Async processing for better performance',
                'Speaker statistics and analytics'
            ],
            'dependencies': dependencies,
            'required_dependencies': ['pydub', 'numpy'],
            'optional_dependencies': ['nemo_toolkit'],
            'supported_formats': ['.wav', '.mp3', '.m4a', '.flac'],
            'limitations': {
                'max_file_size_mb': 100,
                'max_clips': 10,
                'recommended_clip_duration_minutes': 5
            }
        })
        
    except ImportError as e:
        logger.error(f"Speaker diarization service not available: {e}")
        return jsonify({
            'available': False,
            'error': 'Speaker diarization service not available',
            'missing_dependencies': ['speaker_diarization service']
        }), 503

@speaker_diarization_api.route('/validate', methods=['POST'])
@require_session
def validate_diarization_setup():
    """Validate setup for speaker diarization"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    # Check AssemblyAI API key
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        import os
        assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
    
    if not assemblyai_key:
        return jsonify({
            'valid': False,
            'error': 'AssemblyAI API key not configured',
            'requirements': ['assemblyai_api_key']
        }), 400
    
    try:
        from services.speaker_diarization import create_speaker_diarization_service
        
        # Create service instance to validate
        service = create_speaker_diarization_service(assemblyai_key)
        service_info = service.get_service_info()
        
        return jsonify({
            'valid': True,
            'service_info': service_info,
            'setup_complete': True,
            'nemo_available': service_info['capabilities']['nvidia_nemo_integration'],
            'recommendations': [
                'Install NeMo toolkit for advanced speaker verification',
                'Use WAV format for best audio quality',
                'Keep audio clips under 5 minutes for optimal processing'
            ]
        })
        
    except Exception as e:
        logger.error(f"Speaker diarization validation failed: {e}")
        return jsonify({
            'valid': False,
            'error': f'Setup validation failed: {str(e)}',
            'troubleshooting': [
                'Check that all required dependencies are installed',
                'Verify AssemblyAI API key is valid',
                'Try installing missing packages: pip install pydub numpy'
            ]
        }), 500

@speaker_diarization_api.route('/upload-chunks', methods=['POST'])
@require_session
def upload_audio_chunks():
    """Upload multiple audio chunks for speaker diarization"""
    user_id = request.user_id
    config = storage.api_keys_storage.get(user_id, {})
    
    assemblyai_key = config.get('assemblyai_key')
    if not assemblyai_key:
        assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')
    
    if not assemblyai_key:
        return jsonify({'error': 'AssemblyAI API key not configured'}), 400
    
    # Check if files were uploaded
    if 'files' not in request.files:
        return jsonify({'error': 'No audio files provided'}), 400
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400
    
    # Validate number of files
    if len(files) > 10:  # Limit to 10 clips for performance
        return jsonify({
            'error': f'Too many files. Maximum 10 clips allowed, received {len(files)}'
        }), 400
    
    try:
        from services.speaker_diarization import create_speaker_diarization_service
        
        # Create service instance
        service = create_speaker_diarization_service(assemblyai_key)
        
        # Prepare upload directory
        upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 
                                 f'diarization_{user_id}_{int(datetime.now().timestamp())}')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save and validate files
        saved_files = []
        for i, file in enumerate(files):
            if file.filename:
                # Secure filename
                filename = secure_filename(file.filename)
                if not filename:
                    filename = f'audio_clip_{i+1}.wav'
                
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                # Validate file
                validation = service.validate_file_for_transcription(file_path)
                if not validation.get('valid', False):
                    # Clean up and return error
                    import shutil
                    shutil.rmtree(upload_dir, ignore_errors=True)
                    return jsonify({
                        'error': f'Invalid file {filename}: {validation.get("error", "Unknown error")}',
                        'file_validation_errors': [validation]
                    }), 400
                
                saved_files.append({
                    'original_name': file.filename,
                    'saved_path': file_path,
                    'file_info': validation
                })
        
        # Create session for tracking progress
        session_id = f"diarization_{user_id}_{int(datetime.now().timestamp())}"
        active_diarization_sessions[session_id] = {
            'user_id': user_id,
            'files': saved_files,
            'upload_dir': upload_dir,
            'status': 'uploaded',
            'created_at': datetime.now().isoformat(),
            'progress': 0
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'files_uploaded': len(saved_files),
            'files_info': [f['file_info'] for f in saved_files],
            'upload_directory': upload_dir,
            'next_step': 'Start speaker diarization processing',
            'estimated_processing_time_minutes': len(saved_files) * 2  # Rough estimate
        })
        
    except Exception as e:
        logger.error(f"Error uploading audio chunks: {e}")
        return jsonify({
            'error': f'Upload failed: {str(e)}',
            'troubleshooting': [
                'Check that files are valid audio formats',
                'Ensure files are not corrupted',
                'Try uploading fewer files at once'
            ]
        }), 500

@speaker_diarization_api.route('/process/<session_id>', methods=['POST'])
@require_session
def process_speaker_diarization(session_id):
    """Start speaker diarization processing for uploaded chunks"""
    user_id = request.user_id
    
    # Validate session
    if session_id not in active_diarization_sessions:
        return jsonify({'error': 'Invalid or expired session ID'}), 404
    
    session_data = active_diarization_sessions[session_id]
    if session_data['user_id'] != user_id:
        return jsonify({'error': 'Session does not belong to current user'}), 403
    
    if session_data['status'] != 'uploaded':
        return jsonify({'error': f'Session status is {session_data["status"]}, expected "uploaded"'}), 400
    
    try:
        config = storage.api_keys_storage.get(user_id, {})
        assemblyai_key = config.get('assemblyai_key') or os.getenv('ASSEMBLYAI_API_KEY')
        
        from services.speaker_diarization import create_speaker_diarization_service
        
        # Create service instance
        service = create_speaker_diarization_service(assemblyai_key)
        
        # Get file paths
        file_paths = [f['saved_path'] for f in session_data['files']]
        
        # Update session status
        session_data['status'] = 'processing'
        session_data['started_at'] = datetime.now().isoformat()
        
        # Create progress callback
        def progress_callback(progress_data):
            session_data['progress'] = progress_data.get('progress', 0)
            session_data['current_stage'] = progress_data.get('stage', 'unknown')
            session_data['current_message'] = progress_data.get('message', '')
            session_data['last_update'] = datetime.now().isoformat()
        
        # Start processing in background (in a real app, use Celery or similar)
        import threading
        
        def background_processing():
            try:
                results = service.process_file_chunks(file_paths, progress_callback)
                
                session_data['status'] = 'completed'
                session_data['results'] = results
                session_data['completed_at'] = datetime.now().isoformat()
                
            except Exception as e:
                logger.error(f"Speaker diarization processing failed: {e}")
                session_data['status'] = 'error'
                session_data['error'] = str(e)
                session_data['failed_at'] = datetime.now().isoformat()
        
        thread = threading.Thread(target=background_processing)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'status': 'processing',
            'message': 'Speaker diarization processing started',
            'estimated_completion_minutes': len(file_paths) * 3,
            'progress_endpoint': f'/api/speaker-diarization/status/{session_id}'
        })
        
    except Exception as e:
        logger.error(f"Error starting speaker diarization: {e}")
        session_data['status'] = 'error'
        session_data['error'] = str(e)
        
        return jsonify({
            'error': f'Processing failed to start: {str(e)}',
            'session_id': session_id
        }), 500

@speaker_diarization_api.route('/status/<session_id>', methods=['GET'])
@require_session
def get_diarization_status(session_id):
    """Get status of speaker diarization processing"""
    user_id = request.user_id
    
    if session_id not in active_diarization_sessions:
        return jsonify({'error': 'Invalid or expired session ID'}), 404
    
    session_data = active_diarization_sessions[session_id]
    if session_data['user_id'] != user_id:
        return jsonify({'error': 'Session does not belong to current user'}), 403
    
    # Prepare response data
    response_data = {
        'session_id': session_id,
        'status': session_data['status'],
        'progress': session_data.get('progress', 0),
        'current_stage': session_data.get('current_stage', ''),
        'current_message': session_data.get('current_message', ''),
        'created_at': session_data['created_at'],
        'last_update': session_data.get('last_update', session_data['created_at']),
        'files_count': len(session_data['files'])
    }
    
    # Add timing information
    if 'started_at' in session_data:
        response_data['started_at'] = session_data['started_at']
    if 'completed_at' in session_data:
        response_data['completed_at'] = session_data['completed_at']
    if 'failed_at' in session_data:
        response_data['failed_at'] = session_data['failed_at']
    
    # Add results if completed
    if session_data['status'] == 'completed' and 'results' in session_data:
        results = session_data['results']
        response_data['results'] = {
            'unique_speakers': results.get('unique_speakers', []),
            'total_clips_processed': results.get('total_clips_processed', 0),
            'speaker_statistics': results.get('speaker_statistics', {}),
            'processing_metadata': results.get('processing_metadata', {})
        }
        
        # Add transcript display if requested
        if request.args.get('include_transcript') == 'true':
            response_data['transcript'] = results.get('clip_utterances', {})
    
    # Add error details if failed
    if session_data['status'] == 'error':
        response_data['error'] = session_data.get('error', 'Unknown error')
        response_data['troubleshooting'] = [
            'Check that all audio files are valid',
            'Ensure stable internet connection',
            'Try processing fewer files at once',
            'Contact support if issues persist'
        ]
    
    return jsonify(response_data)

@speaker_diarization_api.route('/results/<session_id>', methods=['GET'])
@require_session
def get_diarization_results(session_id):
    """Get detailed results of completed speaker diarization"""
    user_id = request.user_id
    
    if session_id not in active_diarization_sessions:
        return jsonify({'error': 'Invalid or expired session ID'}), 404
    
    session_data = active_diarization_sessions[session_id]
    if session_data['user_id'] != user_id:
        return jsonify({'error': 'Session does not belong to current user'}), 403
    
    if session_data['status'] != 'completed':
        return jsonify({
            'error': f'Session not completed. Current status: {session_data["status"]}',
            'status': session_data['status']
        }), 400
    
    if 'results' not in session_data:
        return jsonify({'error': 'Results not available'}), 500
    
    try:
        results = session_data['results']
        
        # Format transcript for display
        formatted_transcript = ""
        if 'clip_utterances' in results:
            from services.speaker_diarization import create_speaker_diarization_service
            config = storage.api_keys_storage.get(user_id, {})
            assemblyai_key = config.get('assemblyai_key') or os.getenv('ASSEMBLYAI_API_KEY')
            service = create_speaker_diarization_service(assemblyai_key)
            formatted_transcript = service.display_transcript(results['clip_utterances'])
        
        return jsonify({
            'session_id': session_id,
            'status': 'completed',
            'results': {
                'summary': {
                    'unique_speakers_found': len(results.get('unique_speakers', [])),
                    'total_clips_processed': results.get('total_clips_processed', 0),
                    'processing_time': session_data.get('completed_at', ''),
                    'nemo_used': results.get('processing_metadata', {}).get('nemo_available', False)
                },
                'speakers': {
                    'unique_speakers': results.get('unique_speakers', []),
                    'speaker_mapping': results.get('speaker_identity_map', {}),
                    'speaker_statistics': results.get('speaker_statistics', {})
                },
                'transcript': {
                    'formatted': formatted_transcript,
                    'raw_utterances': results.get('clip_utterances', {}),
                    'total_utterances': sum(len(utterances) for utterances in results.get('clip_utterances', {}).values())
                },
                'metadata': results.get('processing_metadata', {}),
                'quality_metrics': {
                    'speaker_identification_confidence': 'high' if results.get('processing_metadata', {}).get('nemo_available') else 'medium',
                    'cross_clip_consistency': 'enabled',
                    'audio_quality_checks': 'performed'
                }
            },
            'export_options': [
                'JSON transcript with speaker labels',
                'Formatted text transcript',
                'Speaker statistics report',
                'CSV export for analysis'
            ]
        })
        
    except Exception as e:
        logger.error(f"Error formatting diarization results: {e}")
        return jsonify({
            'error': f'Failed to format results: {str(e)}',
            'raw_results': session_data.get('results', {})
        }), 500

@speaker_diarization_api.route('/export/<session_id>', methods=['GET'])
@require_session
def export_diarization_results(session_id):
    """Export speaker diarization results in various formats"""
    user_id = request.user_id
    export_format = request.args.get('format', 'json').lower()
    
    if session_id not in active_diarization_sessions:
        return jsonify({'error': 'Invalid or expired session ID'}), 404
    
    session_data = active_diarization_sessions[session_id]
    if session_data['user_id'] != user_id:
        return jsonify({'error': 'Session does not belong to current user'}), 403
    
    if session_data['status'] != 'completed' or 'results' not in session_data:
        return jsonify({'error': 'Results not available for export'}), 400
    
    try:
        results = session_data['results']
        
        if export_format == 'json':
            return jsonify({
                'export_type': 'json',
                'session_id': session_id,
                'export_timestamp': datetime.now().isoformat(),
                'data': results
            })
            
        elif export_format == 'text':
            from services.speaker_diarization import create_speaker_diarization_service
            config = storage.api_keys_storage.get(user_id, {})
            assemblyai_key = config.get('assemblyai_key') or os.getenv('ASSEMBLYAI_API_KEY')
            service = create_speaker_diarization_service(assemblyai_key)
            
            formatted_text = service.display_transcript(results.get('clip_utterances', {}))
            
            from flask import Response
            return Response(
                formatted_text,
                mimetype='text/plain',
                headers={
                    'Content-Disposition': f'attachment; filename=speaker_diarization_{session_id}.txt'
                }
            )
            
        elif export_format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Clip', 'Speaker', 'Start_Time_MS', 'End_Time_MS', 'Duration_MS', 'Text'])
            
            # Write data
            for clip_index, utterances in results.get('clip_utterances', {}).items():
                for utterance in utterances:
                    writer.writerow([
                        clip_index + 1,
                        utterance.get('speaker', 'Unknown'),
                        utterance.get('start', 0),
                        utterance.get('end', 0),
                        utterance.get('end', 0) - utterance.get('start', 0),
                        utterance.get('text', '').replace('\n', ' ')
                    ])
            
            output.seek(0)
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=speaker_diarization_{session_id}.csv'
                }
            )
            
        else:
            return jsonify({
                'error': f'Unsupported export format: {export_format}',
                'supported_formats': ['json', 'text', 'csv']
            }), 400
            
    except Exception as e:
        logger.error(f"Error exporting diarization results: {e}")
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@speaker_diarization_api.route('/cleanup/<session_id>', methods=['DELETE'])
@require_session
def cleanup_diarization_session(session_id):
    """Clean up speaker diarization session and temporary files"""
    user_id = request.user_id
    
    if session_id not in active_diarization_sessions:
        return jsonify({'error': 'Invalid or expired session ID'}), 404
    
    session_data = active_diarization_sessions[session_id]
    if session_data['user_id'] != user_id:
        return jsonify({'error': 'Session does not belong to current user'}), 403
    
    try:
        # Clean up uploaded files
        if 'upload_dir' in session_data and os.path.exists(session_data['upload_dir']):
            import shutil
            shutil.rmtree(session_data['upload_dir'], ignore_errors=True)
            logger.info(f"Cleaned up upload directory: {session_data['upload_dir']}")
        
        # Remove session from memory
        del active_diarization_sessions[session_id]
        
        return jsonify({
            'success': True,
            'message': f'Session {session_id} cleaned up successfully',
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")
        return jsonify({
            'error': f'Cleanup failed: {str(e)}',
            'session_id': session_id
        }), 500

@speaker_diarization_api.route('/sessions', methods=['GET'])
@require_session
def list_user_sessions():
    """List all speaker diarization sessions for current user"""
    user_id = request.user_id
    
    user_sessions = []
    for session_id, session_data in active_diarization_sessions.items():
        if session_data['user_id'] == user_id:
            user_sessions.append({
                'session_id': session_id,
                'status': session_data['status'],
                'created_at': session_data['created_at'],
                'files_count': len(session_data['files']),
                'progress': session_data.get('progress', 0)
            })
    
    return jsonify({
        'user_sessions': user_sessions,
        'total_sessions': len(user_sessions),
        'active_sessions': len([s for s in user_sessions if s['status'] in ['uploaded', 'processing']]),
        'completed_sessions': len([s for s in user_sessions if s['status'] == 'completed'])
    })

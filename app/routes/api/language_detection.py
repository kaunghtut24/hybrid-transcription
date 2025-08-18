"""
Language detection API routes
"""

from flask import Blueprint, request, jsonify
from app.auth import require_session
from app.storage import storage
import logging

logger = logging.getLogger(__name__)
language_detection_api = Blueprint('language_detection_api', __name__)

@language_detection_api.route('/statistics/<session_id>', methods=['GET'])
@require_session
def get_language_statistics(session_id):
    """Get language detection statistics for a session"""
    try:
        # Find the handler for this session
        handler = None
        for sid, conn_handler in storage.active_assemblyai_connections.items():
            if conn_handler.session_id == session_id:
                handler = conn_handler
                break
        
        if not handler:
            return jsonify({'error': 'Session not found or not active'}), 404
        
        language_service = handler.get_language_detection_service()
        if not language_service:
            return jsonify({'error': 'Language detection not available for this session'}), 404
        
        statistics = language_service.get_language_statistics()
        return jsonify({'statistics': statistics})
        
    except Exception as e:
        logger.error(f"Error getting language statistics: {e}")
        return jsonify({'error': str(e)}), 500

@language_detection_api.route('/timeline/<session_id>', methods=['GET'])
@require_session
def get_language_timeline(session_id):
    """Get language detection timeline for a session"""
    try:
        # Find the handler for this session
        handler = None
        for sid, conn_handler in storage.active_assemblyai_connections.items():
            if conn_handler.session_id == session_id:
                handler = conn_handler
                break
        
        if not handler:
            return jsonify({'error': 'Session not found or not active'}), 404
        
        language_service = handler.get_language_detection_service()
        if not language_service:
            return jsonify({'error': 'Language detection not available for this session'}), 404
        
        timeline = language_service.get_language_timeline()
        return jsonify({'timeline': timeline})
        
    except Exception as e:
        logger.error(f"Error getting language timeline: {e}")
        return jsonify({'error': str(e)}), 500

@language_detection_api.route('/export/<session_id>', methods=['GET'])
@require_session
def export_language_data(session_id):
    """Export language detection data for a session"""
    try:
        # Find the handler for this session
        handler = None
        for sid, conn_handler in storage.active_assemblyai_connections.items():
            if conn_handler.session_id == session_id:
                handler = conn_handler
                break
        
        if not handler:
            return jsonify({'error': 'Session not found or not active'}), 404
        
        language_service = handler.get_language_detection_service()
        if not language_service:
            return jsonify({'error': 'Language detection not available for this session'}), 404
        
        export_data = language_service.export_session_data()
        return jsonify({'export_data': export_data})
        
    except Exception as e:
        logger.error(f"Error exporting language data: {e}")
        return jsonify({'error': str(e)}), 500
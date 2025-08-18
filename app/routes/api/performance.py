"""
Performance monitoring API routes
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app.auth import require_session
from app.performance import get_performance_optimizer, log_performance_metric
import logging

logger = logging.getLogger(__name__)
performance_api = Blueprint('performance_api', __name__)

@performance_api.route('/stats', methods=['GET'])
@require_session
def get_performance_stats():
    """Get current performance statistics"""
    try:
        optimizer = get_performance_optimizer()
        
        if optimizer:
            stats = optimizer.get_performance_stats()
            return jsonify({
                'success': True,
                'stats': stats
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Performance optimizer not initialized'
            }), 500
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        return jsonify({'error': 'Failed to get performance stats'}), 500

@performance_api.route('/metric', methods=['POST'])
@require_session
def log_performance_metric_endpoint():
    """Log a performance metric from the frontend"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        metric_type = data.get('type', 'unknown')
        metric_value = data.get('value', 0)
        timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        
        log_performance_metric(metric_type, metric_value, timestamp)
        
        return jsonify({
            'success': True,
            'message': 'Metric logged successfully'
        })
        
    except Exception as e:
        logger.error(f"Error logging performance metric: {e}")
        return jsonify({'error': 'Failed to log metric'}), 500
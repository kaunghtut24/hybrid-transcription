"""
Health check endpoints for cloud deployment platforms
"""

from flask import Blueprint, jsonify
import os
import time

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """Health check endpoint for cloud platforms"""
    try:
        # Basic health checks
        checks = {
            'status': 'healthy',
            'timestamp': int(time.time()),
            'version': '2.0.0',
            'environment': os.environ.get('FLASK_ENV', 'unknown'),
            'services': {
                'api': 'up',
                'websocket': 'up'
            }
        }
        
        # Check if critical environment variables are set
        required_env_vars = ['SECRET_KEY']
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        
        # Test critical imports (especially for Vercel deployment issues)
        try:
            from app.routes.api.config import config_api
            checks['services']['api_imports'] = 'up'
        except Exception as import_error:
            checks['services']['api_imports'] = f'failed: {str(import_error)}'
            checks['status'] = 'degraded'
        
        if missing_vars:
            checks['status'] = 'degraded'
            checks['warnings'] = f"Missing environment variables: {', '.join(missing_vars)}"
        
        return jsonify(checks), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': int(time.time())
        }), 500

@health_bp.route('/health/ready')
def readiness_check():
    """Readiness check for Kubernetes/container orchestration"""
    try:
        # Check if the application is ready to serve traffic
        return jsonify({
            'status': 'ready',
            'timestamp': int(time.time())
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': int(time.time())
        }), 503

@health_bp.route('/health/live')
def liveness_check():
    """Liveness check for Kubernetes/container orchestration"""
    try:
        # Basic liveness check
        return jsonify({
            'status': 'alive',
            'timestamp': int(time.time())
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'dead',
            'error': str(e),
            'timestamp': int(time.time())
        }), 503

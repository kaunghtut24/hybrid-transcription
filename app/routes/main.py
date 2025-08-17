"""
Main application routes (non-API)
"""

from flask import Blueprint, render_template, send_from_directory
from app.performance import lazy_init_performance_optimizer
from app.auth import require_session

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Serve the main application"""
    # Initialize performance optimizer lazily on first request
    lazy_init_performance_optimizer()
    # Temporarily serve the fixed version to avoid JavaScript loading issues
    return render_template('index_fixed.html')

@main_bp.route('/original')
def index_original():
    """Serve the original version of the main application"""
    return render_template('index.html')

@main_bp.route('/speaker-diarization')
def speaker_diarization():
    """Speaker Diarization with Async Chunking feature page"""
    return render_template('speaker_diarization.html')

@main_bp.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@main_bp.route('/favicon.ico')
def favicon():
    """Serve favicon - return empty response to avoid 404"""
    from flask import Response
    return Response('', mimetype='image/x-icon')

@main_bp.route('/simple-test')
def simple_test():
    """Serve a simple test page without complex JavaScript"""
    return render_template('simple_test.html')

@main_bp.route('/fixed')
def index_fixed():
    """Serve the fixed version of the main application"""
    return render_template('index_fixed.html')
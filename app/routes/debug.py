"""
Debug and testing routes
"""

from flask import Blueprint, render_template, send_from_directory

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug')
def debug_frontend():
    """Serve the debug page for frontend troubleshooting"""
    return send_from_directory('.', 'debug_frontend.html')

@debug_bp.route('/test')
def test_page():
    """Serve a simple test page to verify server functionality"""
    return render_template('test.html')

@debug_bp.route('/debug-minimal')
def debug_minimal_page():
    """Serve a minimal debug page to test CSS and basic functionality"""
    return render_template('debug_minimal.html')

@debug_bp.route('/debug-console')
def debug_console_page():
    """Serve a debug console to analyze the main application"""
    return render_template('debug_console.html')

@debug_bp.route('/simple-structure')
def simple_structure_page():
    """Serve a simple structure test page"""
    return render_template('simple_structure.html')

@debug_bp.route('/js-debug')
def js_debug_page():
    """Serve a JavaScript debug test page"""
    return render_template('js_debug.html')

@debug_bp.route('/working-test')
def working_test_page():
    """Serve a working test page to verify basic functionality"""
    return render_template('working_test.html')

@debug_bp.route('/minimal-diagnostic')
def minimal_diagnostic_page():
    """Serve a minimal diagnostic page to test basic JavaScript"""
    return render_template('minimal_diagnostic.html')

@debug_bp.route('/bare-minimum')
def bare_minimum_page():
    """Serve a bare minimum test page with no external JavaScript"""
    return render_template('bare_minimum_test.html')

@debug_bp.route('/browser-test')
def browser_test_page():
    """Serve a simple browser capability test"""
    return render_template('browser_test.html')

@debug_bp.route('/fixed-main')
def fixed_main_page():
    """Serve a fixed main page that works without JavaScript"""
    return render_template('fixed_main.html')
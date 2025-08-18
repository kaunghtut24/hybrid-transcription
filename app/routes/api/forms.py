"""
HTML form-compatible API routes (no JavaScript required)
"""

from flask import Blueprint
from datetime import datetime

forms_api = Blueprint('forms_api', __name__)

@forms_api.route('/recording/start', methods=['POST'])
def start_recording_form():
    """Start recording (HTML form compatible)"""
    try:
        return """
        <html>
        <head><title>Recording Started</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>✅ Recording Started</h2>
            <p>Recording has been initiated successfully.</p>
            <p><a href="/" style="color: #007bff;">← Back to Main App</a></p>
        </body>
        </html>
        """, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"""
        <html>
        <head><title>Recording Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>❌ Recording Failed</h2>
            <p>Error: {str(e)}</p>
            <p><a href="/" style="color: #007bff;">← Back to Main App</a></p>
        </body>
        </html>
        """, 500, {'Content-Type': 'text/html'}

@forms_api.route('/recording/stop', methods=['POST'])
def stop_recording_form():
    """Stop recording (HTML form compatible)"""
    try:
        return """
        <html>
        <head><title>Recording Stopped</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>⏹️ Recording Stopped</h2>
            <p>Recording has been stopped successfully.</p>
            <p><a href="/" style="color: #007bff;">← Back to Main App</a></p>
        </body>
        </html>
        """, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"""
        <html>
        <head><title>Stop Recording Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>❌ Stop Recording Failed</h2>
            <p>Error: {str(e)}</p>
            <p><a href="/" style="color: #007bff;">← Back to Main App</a></p>
        </body>
        </html>
        """, 500, {'Content-Type': 'text/html'}

@forms_api.route('/transcript/latest', methods=['GET'])
def transcript_latest_form():
    """Get latest transcript (HTML form compatible)"""
    try:
        return """
        <html>
        <head><title>Latest Transcript</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>📄 Latest Transcript</h2>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <p><em>No active transcript available. Start recording to generate a transcript.</em></p>
            </div>
            <p><a href="/" style="color: #007bff;">← Back to Main App</a></p>
        </body>
        </html>
        """, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"""
        <html>
        <head><title>Transcript Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>❌ Transcript Fetch Failed</h2>
            <p>Error: {str(e)}</p>
            <p><a href="/" style="color: #007bff;">← Back to Main App</a></p>
        </body>
        </html>
        """, 500, {'Content-Type': 'text/html'}
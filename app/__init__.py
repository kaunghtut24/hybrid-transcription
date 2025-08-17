"""
Flask Web Server for AI Meeting Transcription Assistant
Refactored into modular components for better maintainability
"""

from .app import create_app

__version__ = "2.0.0"
__all__ = ["create_app"]
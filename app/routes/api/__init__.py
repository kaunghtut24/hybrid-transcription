"""
API route modules
"""

from flask import Blueprint
from .session import session_api
from .config import config_api
from .assemblyai import assemblyai_api
from .gemini import gemini_api
from .prompts import prompts_api
from .language_detection import language_detection_api
from .performance import performance_api
from .forms import forms_api
from .speaker_diarization import speaker_diarization_api

# Create main API blueprint
api_bp = Blueprint('api', __name__)

# Register sub-blueprints
api_bp.register_blueprint(session_api, url_prefix='/session')
api_bp.register_blueprint(config_api, url_prefix='/config')
api_bp.register_blueprint(assemblyai_api, url_prefix='/assemblyai')
api_bp.register_blueprint(gemini_api, url_prefix='/gemini')
api_bp.register_blueprint(prompts_api, url_prefix='/prompts')
api_bp.register_blueprint(language_detection_api, url_prefix='/language-detection')
api_bp.register_blueprint(performance_api, url_prefix='/performance')
api_bp.register_blueprint(forms_api)
api_bp.register_blueprint(speaker_diarization_api, url_prefix='/speaker-diarization')
"""
API route modules
Version: 2.0.1 - Fixed import resolution for Vercel deployment
"""

from flask import Blueprint
import logging

# Use absolute imports to ensure reliable resolution in serverless runtimes
# These imports must be absolute to work properly in Vercel's serverless environment
logger = logging.getLogger(__name__)

try:
    from app.routes.api.session import session_api
    from app.routes.api.config import config_api
    from app.routes.api.assemblyai import assemblyai_api
    from app.routes.api.gemini import gemini_api
    from app.routes.api.prompts import prompts_api
    from app.routes.api.language_detection import language_detection_api
    from app.routes.api.performance import performance_api
    from app.routes.api.forms import forms_api
    from app.routes.api.speaker_diarization import speaker_diarization_api
    
    logger.info("Successfully imported all API route modules")
    
except ImportError as e:
    logger.error(f"Failed to import API route modules: {e}")
    raise RuntimeError(f"Critical API import failure: {e}") from e

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
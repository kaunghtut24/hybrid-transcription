"""
Application configuration and environment setup
"""

import os
import secrets

# Load environment variables (optional for production environments)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available in production environments like Vercel
    # Environment variables are handled by the platform
    pass

def get_cors_origins():
    """Helper function to get CORS origins from environment"""
    cors_origins_env = os.environ.get('CORS_ORIGINS', '')
    if cors_origins_env:
        return [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
    return ["*"]  # Fallback for development

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))
    
    # API Keys from environment
    ASSEMBLYAI_API_KEY = os.environ.get('ASSEMBLYAI_API_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Flask settings
    STATIC_FOLDER = 'static'
    TEMPLATE_FOLDER = 'templates'
    
    # File upload settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    
    # CORS settings
    CORS_ORIGINS = get_cors_origins()

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    # Override CORS for development - allow all origins
    CORS_ORIGINS = ["*"]

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # Production CORS settings - use environment or default secure origins
    CORS_ORIGINS = get_cors_origins() if os.environ.get('CORS_ORIGINS') else [
        # Primary Vercel deployments
        "https://ai-meetingnotes.vercel.app",
        "https://hybrid-transcription.vercel.app",
        # Legacy/alternate production backend
        "https://ai-meetingnotes-production.up.railway.app"
    ]

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
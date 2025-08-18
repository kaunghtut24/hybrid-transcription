#!/usr/bin/env python3
"""
Vercel-optimized Flask entry point
No dotenv dependency - uses Vercel environment variables directly
"""

import os
import logging

# No dotenv imports - Vercel handles environment variables
from app import create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the app instance
app, socketio = create_app()

if __name__ == '__main__':
    # Development server (not used on Vercel)
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting Flask application on {host}:{port}")
    logger.info("Environment: development")
    
    socketio.run(
        app,
        host=host,
        port=port,
        debug=False
    )

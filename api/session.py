"""
Vercel Serverless Function: Session Management
Creates and manages user sessions for the AI Meeting Transcription Assistant
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
import jwt

# Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))

def generate_session_token(user_id):
    """Generate a JWT session token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Create a new user session"""
        try:
            # Generate a simple user ID for demo purposes
            client_ip = self.headers.get('x-forwarded-for', '127.0.0.1')
            user_id = hashlib.sha256(f"{client_ip}_{datetime.utcnow()}".encode()).hexdigest()[:16]
            token = generate_session_token(user_id)
            
            response_data = {
                'token': token,
                'user_id': user_id,
                'expires_in': JWT_EXPIRATION_HOURS * 3600
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

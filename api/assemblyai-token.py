"""
Vercel Serverless Function: AssemblyAI Token Management
Provides secure token generation for AssemblyAI WebSocket connections
"""

import os
import json
import secrets
from http.server import BaseHTTPRequestHandler
import jwt
import requests

# Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Shared storage reference (in production, use database)
from .config import api_keys_storage

def verify_session_token(token):
    """Verify and decode JWT session token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(func):
    """Decorator to require authentication"""
    def wrapper(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No authorization token provided'}).encode())
            return
        
        token = auth_header
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_session_token(token)
        if not user_id:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid or expired token'}).encode())
            return
        
        self.user_id = user_id
        return func(self)
    
    return wrapper

class handler(BaseHTTPRequestHandler):
    @require_auth
    def do_POST(self):
        """Get temporary token for AssemblyAI WebSocket connection"""
        try:
            config = api_keys_storage.get(self.user_id, {})
            
            assemblyai_key = config.get('assemblyai_key')
            if not assemblyai_key:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'AssemblyAI API key not configured'}).encode())
                return
            
            # Request temporary token from AssemblyAI
            response = requests.post(
                'https://api.assemblyai.com/v2/realtime/token',
                headers={
                    'Authorization': assemblyai_key,
                    'Content-Type': 'application/json'
                },
                json={'expires_in': 3600},
                timeout=10
            )
            
            if response.status_code == 200:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response.content)
            else:
                self.send_response(response.status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to get AssemblyAI token'}).encode())
        
        except requests.RequestException as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Failed to connect to AssemblyAI'}).encode())
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

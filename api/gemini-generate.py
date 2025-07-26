"""
Vercel Serverless Function: Gemini AI Proxy
Provides secure proxy for Google Gemini AI API requests
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
        """Proxy requests to Gemini API"""
        try:
            config = api_keys_storage.get(self.user_id, {})
            
            gemini_key = config.get('gemini_key')
            if not gemini_key:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Gemini API key not configured'}).encode())
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            model = data.get('model', 'gemini-2.0-flash-exp')
            request_body = data.get('request_body', {})
            
            # Forward request to Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            
            response = requests.post(
                url,
                params={'key': gemini_key},
                headers={'Content-Type': 'application/json'},
                json=request_body,
                timeout=30
            )
            
            self.send_response(response.status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.content)
        
        except requests.RequestException as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Failed to connect to Gemini API'}).encode())
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

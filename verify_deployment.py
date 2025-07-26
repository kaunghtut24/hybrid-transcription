#!/usr/bin/env python3
"""
Deployment Verification Script for AI Meeting Transcription Assistant
Tests all endpoints and verifies the application is ready for production
"""

import requests
import json
import sys
import time
from datetime import datetime

def test_endpoint(url, method='GET', data=None, headers=None, expected_status=200):
    """Test a single endpoint"""
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.status_code == expected_status:
            print(f"✅ {method} {url} - Status: {response.status_code}")
            return True, response
        else:
            print(f"❌ {method} {url} - Expected: {expected_status}, Got: {response.status_code}")
            return False, response
    except Exception as e:
        print(f"❌ {method} {url} - Error: {str(e)}")
        return False, None

def verify_deployment(base_url="http://localhost:5000"):
    """Verify all endpoints are working"""
    print(f"🔍 Verifying deployment at {base_url}")
    print(f"📅 Test started at: {datetime.now().isoformat()}")
    print("-" * 60)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Health check
    total_tests += 1
    success, response = test_endpoint(f"{base_url}/health")
    if success:
        tests_passed += 1
        data = response.json()
        print(f"   Health status: {data.get('status')}")
        print(f"   Version: {data.get('version')}")
    
    # Test 2: Main application
    total_tests += 1
    success, response = test_endpoint(f"{base_url}/")
    if success:
        tests_passed += 1
        print(f"   Content length: {len(response.content)} bytes")
    
    # Test 3: Static files
    total_tests += 1
    success, response = test_endpoint(f"{base_url}/static/app.js")
    if success:
        tests_passed += 1
        print(f"   JavaScript file size: {len(response.content)} bytes")
    
    total_tests += 1
    success, response = test_endpoint(f"{base_url}/static/style.css")
    if success:
        tests_passed += 1
        print(f"   CSS file size: {len(response.content)} bytes")
    
    # Test 4: Create session
    total_tests += 1
    success, response = test_endpoint(f"{base_url}/api/session", method='POST')
    session_token = None
    if success:
        tests_passed += 1
        data = response.json()
        session_token = data.get('token')
        print(f"   Session created, expires in: {data.get('expires_in')} seconds")
    
    # Test 5: Get config (requires session)
    if session_token:
        total_tests += 1
        headers = {'Authorization': f'Bearer {session_token}'}
        success, response = test_endpoint(f"{base_url}/api/config", headers=headers)
        if success:
            tests_passed += 1
            data = response.json()
            print(f"   Config retrieved: AssemblyAI={data.get('assemblyai_configured')}, Gemini={data.get('gemini_configured')}")
    
    # Test 6: Save config (requires session)
    if session_token:
        total_tests += 1
        headers = {'Authorization': f'Bearer {session_token}'}
        config_data = {
            'assemblyai_key': 'test-key-12345',
            'gemini_key': 'test-gemini-key-12345'
        }
        success, response = test_endpoint(f"{base_url}/api/config", method='POST', data=config_data, headers=headers)
        if success:
            tests_passed += 1
            data = response.json()
            print(f"   Config saved: {data.get('message')}")
    
    # Test 7: Unauthorized access
    total_tests += 1
    success, response = test_endpoint(f"{base_url}/api/config", expected_status=401)
    if success:
        tests_passed += 1
        print("   Unauthorized access properly blocked")
    
    # Test 8: 404 handling
    total_tests += 1
    success, response = test_endpoint(f"{base_url}/api/nonexistent", expected_status=404)
    if success:
        tests_passed += 1
        print("   404 handling working correctly")
    
    print("-" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Deployment is ready for production.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return False

def check_cloud_readiness():
    """Check if the application is ready for cloud deployment"""
    print("\n🌐 Cloud Deployment Readiness Check")
    print("-" * 60)
    
    checks = []
    
    # Check if required files exist
    required_files = [
        'app.py',
        'requirements.txt',
        'templates/index.html',
        'static/app.js',
        'static/style.css',
        'vercel.json',
        'firebase.json',
        'Dockerfile',
        'nginx.conf'
    ]
    
    for file in required_files:
        try:
            with open(file, 'r') as f:
                checks.append(f"✅ {file} exists")
        except FileNotFoundError:
            checks.append(f"❌ {file} missing")
    
    # Check environment configuration
    try:
        with open('.env.example', 'r') as f:
            checks.append("✅ Environment template exists")
    except FileNotFoundError:
        checks.append("❌ .env.example missing")
    
    for check in checks:
        print(check)
    
    print("\n📋 Deployment Options Available:")
    print("   • Flask + Nginx (Traditional server)")
    print("   • Docker + Docker Compose")
    print("   • Vercel (Serverless)")
    print("   • Firebase Hosting + Cloud Functions")
    print("   • Google Cloud Platform (App Engine/Cloud Run)")
    
    print("\n📖 See DEPLOYMENT.md for detailed instructions")

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    # Wait a moment for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    success = verify_deployment(base_url)
    check_cloud_readiness()
    
    sys.exit(0 if success else 1)

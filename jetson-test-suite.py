#!/usr/bin/env python3
"""
Jetson AI Meeting Notes Test Suite
Comprehensive testing for Jetson Orin Nano deployment
"""

import requests
import json
import time
import psutil
import subprocess
import sys
from typing import Dict, List, Tuple

class JetsonTestSuite:
    """Test suite for validating Jetson deployment"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        
    def log_result(self, test_name: str, success: bool, message: str = "", duration: float = 0):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'duration': duration,
            'timestamp': time.time()
        }
        self.results.append(result)
        print(f"{status} {test_name} ({duration:.2f}s) - {message}")
    
    def test_system_resources(self) -> bool:
        """Test system resource availability"""
        start_time = time.time()
        try:
            # Check CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                self.log_result("System Resources", False, f"High CPU usage: {cpu_percent}%", time.time() - start_time)
                return False
            
            # Check Memory
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                self.log_result("System Resources", False, f"High memory usage: {memory.percent}%", time.time() - start_time)
                return False
            
            # Check Disk
            disk = psutil.disk_usage('/opt/ai-meeting-notes')
            if disk.percent > 90:
                self.log_result("System Resources", False, f"High disk usage: {disk.percent}%", time.time() - start_time)
                return False
            
            self.log_result("System Resources", True, f"CPU: {cpu_percent}%, RAM: {memory.percent}%, Disk: {disk.percent}%", time.time() - start_time)
            return True
            
        except Exception as e:
            self.log_result("System Resources", False, str(e), time.time() - start_time)
            return False
    
    def test_service_status(self) -> bool:
        """Test systemd service status"""
        start_time = time.time()
        try:
            # Check if service is running
            result = subprocess.run(['systemctl', 'is-active', 'jetson-ai-meeting-notes'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip() == 'active':
                self.log_result("Service Status", True, "Service is active", time.time() - start_time)
                return True
            else:
                self.log_result("Service Status", False, f"Service not active: {result.stdout.strip()}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.log_result("Service Status", False, str(e), time.time() - start_time)
            return False
    
    def test_health_endpoint(self) -> bool:
        """Test application health endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("Health Endpoint", True, f"Status: {data.get('status', 'unknown')}", time.time() - start_time)
                return True
            else:
                self.log_result("Health Endpoint", False, f"HTTP {response.status_code}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.log_result("Health Endpoint", False, str(e), time.time() - start_time)
            return False
    
    def test_api_endpoints(self) -> bool:
        """Test critical API endpoints"""
        start_time = time.time()
        endpoints = [
            ('/api/session/create', 'POST'),
            ('/api/config/initial', 'GET'),
        ]
        
        failed_endpoints = []
        
        for endpoint, method in endpoints:
            try:
                if method == 'GET':
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                else:
                    response = requests.post(f"{self.base_url}{endpoint}", 
                                           json={}, timeout=10)
                
                if response.status_code not in [200, 201]:
                    failed_endpoints.append(f"{endpoint} ({response.status_code})")
                    
            except Exception as e:
                failed_endpoints.append(f"{endpoint} (Error: {str(e)})")
        
        if failed_endpoints:
            self.log_result("API Endpoints", False, f"Failed: {', '.join(failed_endpoints)}", time.time() - start_time)
            return False
        else:
            self.log_result("API Endpoints", True, f"All {len(endpoints)} endpoints working", time.time() - start_time)
            return True
    
    def test_websocket_connection(self) -> bool:
        """Test WebSocket connectivity"""
        start_time = time.time()
        try:
            # Simple test - check if Socket.IO endpoint responds
            response = requests.get(f"{self.base_url}/socket.io/?transport=polling", timeout=10)
            
            if response.status_code == 200:
                self.log_result("WebSocket Connection", True, "Socket.IO endpoint accessible", time.time() - start_time)
                return True
            else:
                self.log_result("WebSocket Connection", False, f"HTTP {response.status_code}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.log_result("WebSocket Connection", False, str(e), time.time() - start_time)
            return False
    
    def test_audio_processing(self) -> bool:
        """Test audio processing capabilities"""
        start_time = time.time()
        try:
            # Check if FFmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                # Check if pydub can be imported
                import pydub
                self.log_result("Audio Processing", True, "FFmpeg and pydub available", time.time() - start_time)
                return True
            else:
                self.log_result("Audio Processing", False, "FFmpeg not available", time.time() - start_time)
                return False
                
        except ImportError:
            self.log_result("Audio Processing", False, "pydub not available", time.time() - start_time)
            return False
        except Exception as e:
            self.log_result("Audio Processing", False, str(e), time.time() - start_time)
            return False
    
    def test_performance_under_load(self) -> bool:
        """Test performance under simulated load"""
        start_time = time.time()
        try:
            # Send multiple concurrent requests
            import concurrent.futures
            import threading
            
            def make_request():
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=5)
                    return response.status_code == 200
                except:
                    return False
            
            # Test with 10 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            success_rate = sum(results) / len(results)
            
            if success_rate >= 0.8:  # 80% success rate
                self.log_result("Performance Load Test", True, f"Success rate: {success_rate:.1%}", time.time() - start_time)
                return True
            else:
                self.log_result("Performance Load Test", False, f"Low success rate: {success_rate:.1%}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.log_result("Performance Load Test", False, str(e), time.time() - start_time)
            return False
    
    def run_all_tests(self) -> Dict:
        """Run all tests and return summary"""
        print("🧪 Starting Jetson AI Meeting Notes Test Suite...")
        print("=" * 60)
        
        tests = [
            self.test_system_resources,
            self.test_service_status,
            self.test_health_endpoint,
            self.test_api_endpoints,
            self.test_websocket_connection,
            self.test_audio_processing,
            self.test_performance_under_load,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        print("=" * 60)
        print(f"📊 Test Summary: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! System is ready for production.")
        elif passed >= total * 0.8:
            print("⚠️  Most tests passed. Review failed tests before production.")
        else:
            print("❌ Multiple test failures. System needs attention before deployment.")
        
        return {
            'total_tests': total,
            'passed_tests': passed,
            'success_rate': passed / total,
            'results': self.results
        }

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:5000"
    
    test_suite = JetsonTestSuite(base_url)
    summary = test_suite.run_all_tests()
    
    # Save results to file
    with open('/opt/ai-meeting-notes/test-results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Exit with appropriate code
    sys.exit(0 if summary['success_rate'] == 1.0 else 1)

if __name__ == '__main__':
    main()

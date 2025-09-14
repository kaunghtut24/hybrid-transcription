#!/usr/bin/env python3
"""
Jetson Orin Nano Performance Configuration
Optimizes Flask application for ARM64 deployment
"""

import os
import psutil
import logging
from typing import Dict, Any

class JetsonPerformanceConfig:
    """Performance configuration optimized for Jetson Orin Nano"""
    
    def __init__(self):
        self.cpu_count = psutil.cpu_count()
        self.memory_gb = psutil.virtual_memory().total / (1024**3)
        self.is_jetson = self._detect_jetson()
        
    def _detect_jetson(self) -> bool:
        """Detect if running on Jetson hardware"""
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().strip()
                return 'jetson' in model.lower()
        except:
            return False
    
    def get_gunicorn_config(self) -> Dict[str, Any]:
        """Get optimized Gunicorn configuration for Jetson"""
        if self.is_jetson:
            # Jetson Orin Nano optimized settings
            workers = min(2, self.cpu_count)  # Conservative worker count
            worker_connections = 100  # Lower connections for stability
            timeout = 60  # Reasonable timeout for ARM64
        else:
            # Fallback for other systems
            workers = min(4, self.cpu_count)
            worker_connections = 200
            timeout = 30
            
        return {
            'bind': '127.0.0.1:5000',
            'workers': workers,
            'worker_class': 'eventlet',
            'worker_connections': worker_connections,
            'timeout': timeout,
            'keepalive': 2,
            'max_requests': 1000,
            'max_requests_jitter': 100,
            'preload_app': True,
            'access_logfile': '/opt/ai-meeting-notes/logs/access.log',
            'error_logfile': '/opt/ai-meeting-notes/logs/error.log',
            'log_level': 'info'
        }
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get optimized Flask configuration"""
        return {
            'MAX_CONTENT_LENGTH': 50 * 1024 * 1024,  # 50MB for Jetson
            'SEND_FILE_MAX_AGE_DEFAULT': 3600,  # 1 hour cache
            'JSON_SORT_KEYS': False,  # Disable sorting for performance
            'JSONIFY_PRETTYPRINT_REGULAR': False,  # Disable pretty printing
            'TEMPLATES_AUTO_RELOAD': False,  # Disable auto-reload in production
        }
    
    def get_socketio_config(self) -> Dict[str, Any]:
        """Get optimized SocketIO configuration"""
        return {
            'async_mode': 'eventlet',
            'ping_timeout': 60,
            'ping_interval': 25,
            'max_http_buffer_size': 1024 * 1024,  # 1MB buffer
            'allow_upgrades': True,
            'transports': ['polling', 'websocket'],
            'cors_allowed_origins': '*',  # Configure properly in production
        }
    
    def optimize_system(self):
        """Apply system-level optimizations"""
        if not self.is_jetson:
            logging.warning("Not running on Jetson hardware, skipping optimizations")
            return
            
        try:
            # Set CPU governor to performance
            os.system('echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor')
            
            # Optimize memory settings
            os.system('echo 10 | sudo tee /proc/sys/vm/swappiness')
            os.system('echo 50 | sudo tee /proc/sys/vm/vfs_cache_pressure')
            
            logging.info("Jetson system optimizations applied")
        except Exception as e:
            logging.error(f"Failed to apply system optimizations: {e}")
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return {
            'enable_metrics': True,
            'metrics_interval': 30,  # seconds
            'log_performance': True,
            'track_memory': True,
            'track_cpu': True,
            'track_gpu': self.is_jetson,  # Only track GPU on Jetson
        }

def create_jetson_config():
    """Create and return Jetson-optimized configuration"""
    config = JetsonPerformanceConfig()
    
    return {
        'gunicorn': config.get_gunicorn_config(),
        'flask': config.get_flask_config(),
        'socketio': config.get_socketio_config(),
        'monitoring': config.get_monitoring_config(),
        'is_jetson': config.is_jetson,
        'hardware_info': {
            'cpu_count': config.cpu_count,
            'memory_gb': round(config.memory_gb, 1),
        }
    }

if __name__ == '__main__':
    # Test the configuration
    config = create_jetson_config()
    print("Jetson Performance Configuration:")
    for section, settings in config.items():
        print(f"\n{section.upper()}:")
        if isinstance(settings, dict):
            for key, value in settings.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {settings}")

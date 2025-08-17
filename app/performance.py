"""
Performance optimization and monitoring
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Global performance optimizer instance
performance_optimizer = None

def lazy_init_performance_optimizer():
    """Initialize performance optimizer lazily to avoid startup delays"""
    global performance_optimizer
    if performance_optimizer is None:
        try:
            from optimize_performance import initialize_performance_optimizer
            from flask import current_app
            performance_optimizer = initialize_performance_optimizer(current_app)
            logger.info("Performance optimizer initialized successfully")
        except Exception as e:
            logger.warning(f"Performance optimizer initialization failed: {e}")
            # Create a minimal fallback optimizer
            performance_optimizer = type('MinimalOptimizer', (), {
                'optimize': lambda: None,
                'get_metrics': lambda: {}
            })()

def get_performance_optimizer():
    """Get the performance optimizer instance"""
    return performance_optimizer

def log_performance_metric(metric_type, metric_value, timestamp=None):
    """Log a performance metric"""
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    
    logger.info(f"Performance metric - {metric_type}: {metric_value} at {timestamp}")
    
    # In production, you might want to store this in a database
    return True
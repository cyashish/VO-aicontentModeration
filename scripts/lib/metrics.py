"""
Prometheus metrics exporter
"""
import os
import logging
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from functools import wraps
import time

logger = logging.getLogger(__name__)

# Counters
content_processed = Counter('moderation_content_processed_total', 'Total content processed', ['decision', 'content_type'])
ml_inferences = Counter('moderation_ml_inferences_total', 'Total ML inferences', ['model'])
violations_detected = Counter('moderation_violations_total', 'Total violations detected', ['violation_type'])
chat_messages = Counter('moderation_chat_messages_total', 'Total chat messages', ['decision'])

# Histograms (for latency)
processing_latency = Histogram('moderation_processing_duration_seconds', 'Processing duration', ['tier'])
ml_latency = Histogram('moderation_ml_duration_seconds', 'ML inference duration', ['model'])
flink_latency = Histogram('moderation_flink_duration_seconds', 'Flink processing duration')

# Gauges (for current state)
queue_depth = Gauge('moderation_queue_depth', 'Current review queue depth', ['priority'])
active_users = Gauge('moderation_active_users', 'Currently active users')
sla_compliance = Gauge('moderation_sla_compliance_percent', 'SLA compliance percentage', ['priority'])


class MetricsExporter:
    """Prometheus metrics exporter"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.server_started = False
    
    def start(self):
        """Start Prometheus HTTP server"""
        if not self.server_started:
            start_http_server(self.port)
            self.server_started = True
            logger.info(f"Prometheus metrics server started on port {self.port}")
    
    @staticmethod
    def track_processing(tier: str):
        """Decorator to track processing time"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    processing_latency.labels(tier=tier).observe(duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    processing_latency.labels(tier=f"{tier}_error").observe(duration)
                    raise
            return wrapper
        return decorator
    
    @staticmethod
    def record_content(decision: str, content_type: str):
        """Record content moderation decision"""
        content_processed.labels(decision=decision, content_type=content_type).inc()
    
    @staticmethod
    def record_ml_inference(model: str, duration: float):
        """Record ML inference"""
        ml_inferences.labels(model=model).inc()
        ml_latency.labels(model=model).observe(duration)
    
    @staticmethod
    def record_violation(violation_type: str):
        """Record violation detection"""
        violations_detected.labels(violation_type=violation_type).inc()
    
    @staticmethod
    def record_chat(decision: str, latency_ms: float):
        """Record chat message decision"""
        chat_messages.labels(decision=decision).inc()
        flink_latency.observe(latency_ms / 1000.0)
    
    @staticmethod
    def update_queue_depth(priority: str, depth: int):
        """Update queue depth gauge"""
        queue_depth.labels(priority=priority).set(depth)
    
    @staticmethod
    def update_sla_compliance(priority: str, compliance_pct: float):
        """Update SLA compliance"""
        sla_compliance.labels(priority=priority).set(compliance_pct)


# Singleton instance
metrics = MetricsExporter(port=int(os.getenv('METRICS_PORT', '8000')))

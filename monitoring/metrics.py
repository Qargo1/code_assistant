from prometheus_client import start_http_server, Gauge, Counter, Histogram
import psutil
import time
import logging

class SystemMetrics:
    def __init__(self):
        # Инициализация метрик Prometheus
        self.cpu_usage = Gauge('system_cpu_percent', 'CPU usage percentage')
        self.memory_usage = Gauge('system_memory_usage', 'Memory usage in MB')
        self.jobs_processed = Counter('jobs_processed_total', 'Total processed jobs')
        self.job_duration = Histogram('job_duration_seconds', 'Job processing time')
        self.vector_db_size = Gauge('vector_db_size', 'Number of vectors in DB')
        
        self.logger = logging.getLogger(__name__)

    def start_metrics_server(self, port=8000):
        """Запуск сервера метрик"""
        start_http_server(port)
        self.logger.info(f"Metrics server started on port {port}")

    def update_system_metrics(self):
        """Обновление системных метрик"""
        while True:
            self.cpu_usage.set(psutil.cpu_percent())
            self.memory_usage.set(psutil.virtual_memory().used / 1024 / 1024)
            time.sleep(5)

class CodebaseMetrics:
    def __init__(self):
        self.files_analyzed = Counter('files_analyzed', 'Files analyzed', ['language'])
        self.analysis_errors = Counter('analysis_errors', 'Analysis errors', ['type'])
        self.cache_hits = Counter('cache_hits_total', 'Cache hit rate')
        
# В monitoring/metrics.py
class CacheMetrics:
    def __init__(self):
        self.hits = Counter('cache_hits_total', 'Cache hits')
        self.misses = Counter('cache_misses_total', 'Cache misses')
        self.size = Gauge('cache_size_bytes', 'Cache size in bytes')

class LayeredCache:
    def get(self, key):
        for backend in self.backends:
            if value := backend.get(key):
                metrics.cache_hits.inc()
                return value
        metrics.cache_misses.inc()
        return None
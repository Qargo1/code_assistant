import psutil
import threading
import time
from datetime import datetime
import logging

class ResourceMonitor:
    def __init__(self, db_manager, interval=5):
        """Initialize the resource monitor."""
        self.db_manager = db_manager
        self.interval = interval
        self.monitoring = False
        self.monitor_thread = None
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start resource monitoring."""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            print("<self>Resource monitoring started</self>")

    def stop(self):
        """Stop resource monitoring."""
        if self.monitoring:
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join()
            print("<self>Resource monitoring stopped</self>")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                self._store_metrics(metrics)
                time.sleep(self.interval)
            except Exception as e:
                print(f"<error>Resource monitoring error: {str(e)}</error>")

    def _collect_metrics(self):
        """Collect system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                    'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'process': self._get_process_metrics()
            }
            
            return metrics
        except Exception as e:
            print(f"<error>Failed to collect metrics: {str(e)}</error>")
            raise

    def _get_process_metrics(self):
        """Get metrics for the current process."""
        try:
            process = psutil.Process()
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'memory_info': process.memory_info()._asdict(),
                'num_threads': process.num_threads(),
                'open_files': len(process.open_files()),
                'connections': len(process.connections())
            }
        except Exception as e:
            print(f"<error>Failed to get process metrics: {str(e)}</error>")
            return {}

    def _store_metrics(self, metrics):
        """Store collected metrics in the database."""
        try:
            self.db_manager.store_analysis_result(
                file_path='system',  # Using 'system' as a special identifier
                analysis_type='resource_metrics',
                result=metrics
            )
        except Exception as e:
            print(f"<error>Failed to store metrics: {str(e)}</error>")

    def get_metrics_history(self, time_range=None):
        """Get historical metrics from the database."""
        try:
            results = self.db_manager.get_file_analysis(
                file_path='system',
                analysis_type='resource_metrics'
            )
            
            # Filter by time range if specified
            if time_range:
                start_time = datetime.now() - time_range
                results = [
                    r for r in results
                    if datetime.fromisoformat(r[1]['timestamp']) >= start_time
                ]
            
            return results
        except Exception as e:
            print(f"<error>Failed to get metrics history: {str(e)}</error>")
            raise

    def get_resource_warning(self, cpu_threshold=80, memory_threshold=80, disk_threshold=90):
        """Check if any resource metrics exceed warning thresholds."""
        try:
            metrics = self._collect_metrics()
            warnings = []
            
            if metrics['cpu']['percent'] > cpu_threshold:
                warnings.append(f"High CPU usage: {metrics['cpu']['percent']}%")
            
            if metrics['memory']['percent'] > memory_threshold:
                warnings.append(f"High memory usage: {metrics['memory']['percent']}%")
            
            if metrics['disk']['percent'] > disk_threshold:
                warnings.append(f"High disk usage: {metrics['disk']['percent']}%")
            
            return warnings if warnings else None
            
        except Exception as e:
            print(f"<error>Failed to check resource warnings: {str(e)}</error>")
            raise

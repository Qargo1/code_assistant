import redis
from rq import Queue
from rq.queue import get_failed_queue
import logging
import json
from monitoring.metrics import CodebaseMetrics


metrics = CodebaseMetrics()


class PriorityAnalysisQueue:
    def __init__(self):
        self.redis_conn = redis.Redis(host='localhost', port=6379, db=0)
        self.high_priority = Queue('high', connection=self.redis_conn)
        self.medium_priority = Queue('medium', connection=self.redis_conn)
        self.low_priority = Queue('low', connection=self.redis_conn)
        
        self.logger = logging.getLogger(__name__)

    def _determine_priority(self, file_metadata):
        """Вычисление приоритета на основе метаданных файла"""
        priority_score = (
            len(file_metadata.get('dependencies', [])) * 0.4 +
            file_metadata.get('change_frequency', 0) * 0.3 +
            file_metadata.get('complexity', 0) * 0.3
        )
        
        if priority_score > 0.7:
            return self.high_priority
        elif priority_score > 0.4:
            return self.medium_priority
        return self.low_priority

    def add_task(self, file_path, metadata):
        """Добавление задачи в очередь"""
        try:
            queue = self._determine_priority(metadata)
            job = queue.enqueue(
                'tasks.sample_task.analyze_file',
                args=(file_path, metadata),
                meta={'file_path': file_path}
            )
            self.logger.info(f"Task added: {job.id} for {file_path}")
            
            metrics.jobs_processed.inc()
            metrics.files_analyzed.labels(language=lang).inc()
            
            metadata['commit_hash'] = get_current_commit_hash()
            
            return job.id
        except redis.exceptions.RedisError as e:
            self.logger.error(f"Redis error: {str(e)}")
            raise

    def restart_failed_jobs(self):
        """Перезапуск упавших задач"""
        failed_queue = get_failed_queue(self.redis_conn)
        for job in failed_queue.get_jobs():
            failed_queue.requeue(job.id)
            self.logger.warning(f"Restarted failed job: {job.id}")
        
            
class AnalysisWorker:
    def perform_job(self, job):
        with metrics.job_duration.time():
            return
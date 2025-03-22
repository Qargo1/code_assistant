from rq import Worker
from core.queue.priority_queue import PriorityAnalysisQueue

class AnalysisWorker(Worker):
    def __init__(self, queues=None, *args, **kwargs):
        queues = ['high', 'medium', 'low'] if not queues else queues
        super().__init__(queues, *args, **kwargs)
        self.queue_system = PriorityAnalysisQueue()

    def handle_exception(self, job, exc_type, exc_value, traceback):
        """Кастомная обработка ошибок"""
        self.queue_system.logger.error(
            f"Job {job.id} failed: {str(exc_value)}"
        )
        return super().handle_exception(job, exc_type, exc_value, traceback)
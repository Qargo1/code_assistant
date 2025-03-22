from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

class AnalysisScheduler:
    def __init__(self, db_manager, csharp_analyzer=None, java_analyzer=None):
        """Initialize the scheduler with analyzers."""
        self.scheduler = BackgroundScheduler()
        self.db_manager = db_manager
        self.csharp_analyzer = csharp_analyzer
        self.java_analyzer = java_analyzer
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the scheduler."""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                print("<self>Scheduler started successfully</self>")
        except Exception as e:
            print(f"<error>Failed to start scheduler: {str(e)}</error>")
            raise

    def stop(self):
        """Stop the scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                print("<self>Scheduler stopped successfully</self>")
        except Exception as e:
            print(f"<error>Failed to stop scheduler: {str(e)}</error>")
            raise

    def schedule_analysis(self, file_path, interval='daily', specific_time=None):
        """Schedule analysis for a specific file."""
        try:
            # Determine file type and appropriate analyzer
            if file_path.endswith('.cs'):
                analyzer = self.csharp_analyzer
                analysis_type = 'csharp'
            elif file_path.endswith('.java'):
                analyzer = self.java_analyzer
                analysis_type = 'java'
            else:
                raise ValueError(f"Unsupported file type: {file_path}")

            if not analyzer:
                raise ValueError(f"No analyzer available for {analysis_type}")

            # Create the job
            job_id = f"analysis_{file_path}_{analysis_type}"
            
            # Configure trigger
            if interval == 'daily' and specific_time:
                trigger = CronTrigger(
                    hour=specific_time.hour,
                    minute=specific_time.minute
                )
            elif interval == 'hourly':
                trigger = CronTrigger(minute=0)
            else:
                trigger = CronTrigger(hour=0, minute=0)  # Default to midnight

            # Schedule the job
            self.scheduler.add_job(
                self._run_analysis,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                args=[file_path, analyzer, analysis_type]
            )

            print(f"<self>Scheduled {interval} analysis for {file_path}</self>")
            return job_id

        except Exception as e:
            print(f"<error>Failed to schedule analysis: {str(e)}</error>")
            raise

    def _run_analysis(self, file_path, analyzer, analysis_type):
        """Run the analysis job."""
        try:
            print(f"<self>Starting analysis of {file_path}</self>")
            
            # Run analysis
            results = analyzer.analyze_file(file_path)
            
            # Store results
            self.db_manager.store_analysis_result(
                file_path=file_path,
                analysis_type=analysis_type,
                result=results
            )
            
            # Update file record
            self.db_manager.add_file(
                path=file_path,
                language=analysis_type,
                metadata={
                    "last_successful_analysis": datetime.now().isoformat(),
                    "analysis_status": "success"
                }
            )
            
            print(f"<self>Completed analysis of {file_path}</self>")
            
        except Exception as e:
            error_msg = str(e)
            print(f"<error>Analysis failed for {file_path}: {error_msg}</error>")
            
            # Update file record with error
            self.db_manager.add_file(
                path=file_path,
                language=analysis_type,
                metadata={
                    "last_failed_analysis": datetime.now().isoformat(),
                    "analysis_status": "error",
                    "error_message": error_msg
                }
            )

    def list_scheduled_jobs(self):
        """List all scheduled analysis jobs."""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
            return jobs
        except Exception as e:
            print(f"<error>Failed to list jobs: {str(e)}</error>")
            raise

    def remove_job(self, job_id):
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            print(f"<self>Removed job {job_id}</self>")
        except Exception as e:
            print(f"<error>Failed to remove job {job_id}: {str(e)}</error>")
            raise

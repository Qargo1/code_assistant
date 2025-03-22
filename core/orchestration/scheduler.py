# В core/orchestration/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

def start_vcs_polling():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_repository_changes,
        'interval',
        minutes=5,
        args=[config['repo_path']]
    )
    scheduler.start()

def check_repository_changes(repo_path):
    manager = GitManager(repo_path)
    changes = manager.get_changed_files()
    if changes:
        logger.info(f"Found {len(changes)} new changes")
        process_changes(changes)
import git
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from core.database.connection import get_session
from core.database.models import FileMetadata
import logging

class GitManager:
    def __init__(self, repo_path: str):
        self.repo = git.Repo(repo_path)
        self.logger = logging.getLogger(__name__)

    def get_changed_files(self, commit_range: str = "HEAD~1..HEAD") -> List[Dict]:
        """Получение измененных файлов между коммитами"""
        diff = self.repo.git.diff(commit_range, name_status=True)
        return self._parse_diff(diff)

    def _parse_diff(self, diff_output: str) -> List[Dict]:
        """Парсинг вывода git diff"""
        changes = []
        for line in diff_output.split('\n'):
            if not line:
                continue
            status, path = line.split('\t', 1)
            changes.append({
                'status': status[0],
                'path': str(Path(self.repo.working_dir) / path),
                'commit_hash': self.repo.head.commit.hexsha
            })
        return changes

    def auto_commit_metadata(self):
        """Автоматический коммит изменений метаданных"""
        with get_session() as session:
            modified_files = session.query(FileMetadata).filter(
                FileMetadata.last_analyzed > self.last_commit_time()
            ).all()

            if modified_files:
                self.repo.git.add('code_knowledge.db')
                self.repo.index.commit(f"Auto-commit metadata at {datetime.now()}")

    def last_commit_time(self) -> datetime:
        """Время последнего коммита"""
        return self.repo.head.commit.committed_datetime

class ChangeTracker:
    def __init__(self, repo_path: str):
        self.git_manager = GitManager(repo_path)
        self.trigger_hooks()

    def trigger_hooks(self):
        """Установка git hooks для автоматического трекинга"""
        hook_script = """#!/bin/sh
        python -c "from core.vcs.change_tracker import track_changes; track_changes()"
        """
        hook_path = Path(self.git_manager.repo.git_dir) / "hooks/post-commit"
        hook_path.write_text(hook_script)
        hook_path.chmod(0o755)

    @staticmethod
    def track_changes():
        """Обработчик изменений"""
        from core.automation.priority_queue import PriorityAnalysisQueue
        manager = GitManager('.')
        changed_files = manager.get_changed_files()
        
        queue = PriorityAnalysisQueue()
        for file in changed_files:
            queue.add_task(file['path'], {'change_type': file['status']})
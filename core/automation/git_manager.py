from git import Repo
from datetime import datetime
import os
import logging

class GitManager:
    def __init__(self, repo_path, db_manager):
        """Initialize Git manager with repository path."""
        self.repo_path = repo_path
        self.db_manager = db_manager
        self.repo = Repo(repo_path)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def analyze_changes(self, commit_range=None):
        """Analyze changes in the specified commit range or since last analysis."""
        try:
            if not commit_range:
                # Get last analyzed commit from DB
                last_commit = self._get_last_analyzed_commit()
                if last_commit:
                    commit_range = f"{last_commit}..HEAD"
                else:
                    # Analyze last 10 commits if no previous analysis
                    commit_range = "HEAD~10..HEAD"

            print(f"<self>Analyzing changes in range: {commit_range}</self>")
            
            changes = self._get_file_changes(commit_range)
            self._process_changes(changes)
            
            # Store analysis metadata
            self._update_analysis_state()
            
            return changes
            
        except Exception as e:
            print(f"<error>Failed to analyze changes: {str(e)}</error>")
            raise

    def _get_last_analyzed_commit(self):
        """Get the last analyzed commit from database."""
        try:
            # Query analysis results for git metadata
            results = self.db_manager.get_file_analysis(
                file_path=self.repo_path,
                analysis_type="git_analysis"
            )
            
            if results and results[0][1].get('last_commit'):
                return results[0][1]['last_commit']
            return None
            
        except Exception as e:
            print(f"<error>Failed to get last analyzed commit: {str(e)}</error>")
            return None

    def _get_file_changes(self, commit_range):
        """Get file changes in the specified commit range."""
        changes = {
            'modified': [],
            'added': [],
            'deleted': [],
            'commits': []
        }
        
        try:
            # Get commits in range
            commits = list(self.repo.iter_commits(commit_range))
            
            for commit in commits:
                commit_info = {
                    'hash': commit.hexsha,
                    'author': commit.author.name,
                    'date': commit.committed_datetime.isoformat(),
                    'message': commit.message.strip(),
                    'changes': []
                }
                
                # Get parent commit for diff
                parent = commit.parents[0] if commit.parents else None
                
                if parent:
                    # Get changed files
                    for diff in commit.diff(parent):
                        change = {
                            'path': diff.a_path or diff.b_path,
                            'type': self._get_change_type(diff),
                            'insertions': diff.diff.count(b'+'),
                            'deletions': diff.diff.count(b'-')
                        }
                        
                        commit_info['changes'].append(change)
                        
                        # Track overall file changes
                        if change['type'] == 'M':
                            changes['modified'].append(change['path'])
                        elif change['type'] == 'A':
                            changes['added'].append(change['path'])
                        elif change['type'] == 'D':
                            changes['deleted'].append(change['path'])
                
                changes['commits'].append(commit_info)
            
            # Remove duplicates
            changes['modified'] = list(set(changes['modified']))
            changes['added'] = list(set(changes['added']))
            changes['deleted'] = list(set(changes['deleted']))
            
            return changes
            
        except Exception as e:
            print(f"<error>Failed to get file changes: {str(e)}</error>")
            raise

    def _get_change_type(self, diff):
        """Get the type of change from a diff object."""
        if diff.new_file:
            return 'A'  # Added
        elif diff.deleted_file:
            return 'D'  # Deleted
        else:
            return 'M'  # Modified

    def _process_changes(self, changes):
        """Process and store the analyzed changes."""
        try:
            # Store commit history
            for commit in changes['commits']:
                self.db_manager.store_analysis_result(
                    file_path=self.repo_path,
                    analysis_type="git_commit",
                    result=commit
                )
            
            # Update file statuses
            for file_path in changes['modified']:
                if os.path.exists(os.path.join(self.repo_path, file_path)):
                    self.db_manager.add_file(
                        path=file_path,
                        language=self._get_file_language(file_path),
                        metadata={
                            "last_modified": datetime.now().isoformat(),
                            "status": "modified"
                        }
                    )
            
            for file_path in changes['added']:
                self.db_manager.add_file(
                    path=file_path,
                    language=self._get_file_language(file_path),
                    metadata={
                        "added_at": datetime.now().isoformat(),
                        "status": "new"
                    }
                )
            
            for file_path in changes['deleted']:
                self.db_manager.add_file(
                    path=file_path,
                    language=self._get_file_language(file_path),
                    metadata={
                        "deleted_at": datetime.now().isoformat(),
                        "status": "deleted"
                    }
                )
                
        except Exception as e:
            print(f"<error>Failed to process changes: {str(e)}</error>")
            raise

    def _update_analysis_state(self):
        """Update the Git analysis state in the database."""
        try:
            current_commit = self.repo.head.commit.hexsha
            self.db_manager.store_analysis_result(
                file_path=self.repo_path,
                analysis_type="git_analysis",
                result={
                    "last_commit": current_commit,
                    "analysis_date": datetime.now().isoformat()
                }
            )
        except Exception as e:
            print(f"<error>Failed to update analysis state: {str(e)}</error>")
            raise

    def _get_file_language(self, file_path):
        """Determine the programming language of a file."""
        if file_path.endswith('.cs'):
            return 'csharp'
        elif file_path.endswith('.java'):
            return 'java'
        else:
            return 'unknown'

    def get_file_history(self, file_path):
        """Get the commit history for a specific file."""
        try:
            history = []
            for commit in self.repo.iter_commits(paths=file_path):
                history.append({
                    'hash': commit.hexsha,
                    'author': commit.author.name,
                    'date': commit.committed_datetime.isoformat(),
                    'message': commit.message.strip()
                })
            return history
        except Exception as e:
            print(f"<error>Failed to get file history: {str(e)}</error>")
            raise

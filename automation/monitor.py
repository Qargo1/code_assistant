from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import time
from datetime import datetime
import logging

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self, db_manager, csharp_analyzer=None, java_analyzer=None):
        """Initialize the file change handler."""
        self.db_manager = db_manager
        self.csharp_analyzer = csharp_analyzer
        self.java_analyzer = java_analyzer
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Track modifications to prevent duplicate events
        self._last_modified = {}

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = event.src_path
        current_time = time.time()
        
        # Check if we've processed this file recently (debounce)
        if file_path in self._last_modified:
            if current_time - self._last_modified[file_path] < 1:  # 1 second debounce
                return
                
        self._last_modified[file_path] = current_time
        
        try:
            # Determine file type and appropriate analyzer
            if file_path.endswith('.cs') and self.csharp_analyzer:
                self._analyze_file(file_path, self.csharp_analyzer, 'csharp')
            elif file_path.endswith('.java') and self.java_analyzer:
                self._analyze_file(file_path, self.java_analyzer, 'java')
                
        except Exception as e:
            print(f"<error>Failed to process modified file {file_path}: {str(e)}</error>")

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
            
        file_path = event.src_path
        try:
            # Add new file to database
            if file_path.endswith(('.cs', '.java')):
                language = 'csharp' if file_path.endswith('.cs') else 'java'
                self.db_manager.add_file(
                    path=file_path,
                    language=language,
                    metadata={
                        "created_at": datetime.now().isoformat(),
                        "status": "pending_analysis"
                    }
                )
                print(f"<self>Added new file to monitoring: {file_path}</self>")
                
        except Exception as e:
            print(f"<error>Failed to process new file {file_path}: {str(e)}</error>")

    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
            
        file_path = event.src_path
        try:
            # Update file status in database
            if file_path.endswith(('.cs', '.java')):
                self.db_manager.add_file(
                    path=file_path,
                    language='unknown',
                    metadata={
                        "deleted_at": datetime.now().isoformat(),
                        "status": "deleted"
                    }
                )
                print(f"<self>Marked file as deleted: {file_path}</self>")
                
        except Exception as e:
            print(f"<error>Failed to process deleted file {file_path}: {str(e)}</error>")

    def _analyze_file(self, file_path, analyzer, language):
        """Analyze a file using the appropriate analyzer."""
        try:
            print(f"<self>Analyzing modified file: {file_path}</self>")
            
            # Run analysis
            results = analyzer.analyze_file(file_path)
            
            # Store results
            self.db_manager.store_analysis_result(
                file_path=file_path,
                analysis_type=language,
                result=results
            )
            
            # Update file record
            self.db_manager.add_file(
                path=file_path,
                language=language,
                metadata={
                    "last_analysis": datetime.now().isoformat(),
                    "status": "analyzed"
                }
            )
            
            print(f"<self>Completed analysis of modified file: {file_path}</self>")
            
        except Exception as e:
            print(f"<error>Analysis failed for {file_path}: {str(e)}</error>")
            # Update file record with error
            self.db_manager.add_file(
                path=file_path,
                language=language,
                metadata={
                    "last_error": datetime.now().isoformat(),
                    "status": "error",
                    "error_message": str(e)
                }
            )

class FileMonitor:
    def __init__(self, path, db_manager, csharp_analyzer=None, java_analyzer=None):
        """Initialize the file monitor."""
        self.path = path
        self.event_handler = CodeChangeHandler(
            db_manager,
            csharp_analyzer,
            java_analyzer
        )
        self.observer = Observer()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start monitoring the specified path."""
        try:
            self.observer.schedule(
                self.event_handler,
                self.path,
                recursive=True
            )
            self.observer.start()
            print(f"<self>Started monitoring: {self.path}</self>")
            
        except Exception as e:
            print(f"<error>Failed to start file monitor: {str(e)}</error>")
            raise

    def stop(self):
        """Stop monitoring."""
        try:
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join()
                print("<self>Stopped file monitoring</self>")
                
        except Exception as e:
            print(f"<error>Failed to stop file monitor: {str(e)}</error>")
            raise

    def scan_existing_files(self):
        """Scan existing files in the monitored directory."""
        try:
            print("<self>Scanning existing files...</self>")
            for root, _, files in os.walk(self.path):
                for file in files:
                    if file.endswith(('.cs', '.java')):
                        file_path = os.path.join(root, file)
                        self.event_handler.on_created(
                            type('Event', (), {'is_directory': False, 'src_path': file_path})()
                        )
            print("<self>Initial file scan completed</self>")
            
        except Exception as e:
            print(f"<error>Failed to scan existing files: {str(e)}</error>")
            raise

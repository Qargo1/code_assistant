# core/analysis/multilang_analyzer.py
from pathlib import Path
from .bridges import CSharpAnalyzer, JavaAnalyzer

class MultiLanguageAnalyzer:
    def __init__(self):
        self.analyzers = {
            ".cs": CSharpAnalyzer(),
            ".java": JavaAnalyzer()
        }
    
    def analyze(self, file_path: Path) -> dict:
        """Р
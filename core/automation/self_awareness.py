import os
import subprocess
from pathlib import Path
from typing import List, Dict
from git.repo import Repo

class SelfKnowledge:
    def __init__(self):
        self.root = Path(__file__).parent.parent
        self.mirror_dir = self.root / ".self/code"
        self._init_vfs()
        
    def _init_vfs(self):
        """Инициализация виртуальной файловой системы"""
        self.mirror_dir.mkdir(exist_ok=True, parents=True)
        
        # Создаем зеркало кода
        if not (self.mirror_dir / ".git").exists():
            Repo.init(self.mirror_dir)
            
        self._sync_code_mirror()

    def _sync_code_mirror(self):
        """Синхронизация текущего кода в зеркало"""
        try:
            subprocess.run([
                "rsync", "-a", 
                "--exclude", ".self",
                "--exclude", ".git",
                "--exclude", "__pycache__",
                str(self.root) + "/",
                str(self.mirror_dir)
            ], check=True)
            
            repo = Repo(self.mirror_dir)
            repo.git.add(A=True)
            repo.index.commit("Auto-commit bot self-knowledge")
        except Exception as e:
            print(f"Self-sync error: {str(e)}")

    def get_self_structure(self) -> Dict:
        """Получение структуры собственного кода"""
        structure = {
            "name": "CodeAssistant",
            "version": self._get_version(),
            "components": []
        }
        
        for path in self.mirror_dir.rglob("*"):
            if path.is_file():
                structure["components"].append({
                    "path": str(path.relative_to(self.mirror_dir)),
                    "type": "file",
                    "language": path.suffix[1:] if path.suffix else "unknown"
                })
        return structure

    def read_self_file(self, file_path: str) -> str:
        """Чтение собственного файла"""
        full_path = self.mirror_dir / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"Self-file {file_path} not found")
            
        return full_path.read_text()

    def _get_version(self) -> str:
        """Получение версии из setup.py"""
        setup_path = self.mirror_dir / "setup.py"
        with open(setup_path) as f:
            for line in f:
                if "version=" in line:
                    return line.split("=")[1].strip(" ,'\")")
        return "unknown"
import pytest
import tempfile
from git import Repo
from pathlib import Path
from core.vcs.git_integration import GitManager

@pytest.fixture
def test_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Repo.init(tmpdir)
        # Создаем тестовый файл
        (Path(tmpdir) / "test.txt").write_text("initial")
        repo.git.add(all=True)
        repo.index.commit("Initial commit")
        yield tmpdir

def test_changed_files(test_repo):
    manager = GitManager(test_repo)
    # Делаем изменения
    (Path(test_repo) / "test.txt").write_text("modified")
    repo = Repo(test_repo)
    repo.git.add(all=True)
    repo.index.commit("Modify file")
    
    changes = manager.get_changed_files("HEAD~1..HEAD")
    assert len(changes) == 1
    assert changes[0]['status'] == 'M'
    assert "test.txt" in changes[0]['path']
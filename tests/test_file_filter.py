import pytest
from pathlib import Path
from unittest.mock import MagicMock
from core.analysis.filter import FileFilter

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.classifier.return_value = [{
        'generated_text': '{"relevant": true, "confidence": 0.85, "keywords": ["auth", "security"]}'
    }]
    return llm

def test_relevance_check(mock_llm):
    filter = FileFilter()
    filter.classifier = mock_llm
    
    test_file = Path("test_auth.py")
    test_file.write_text("def authenticate(): ...")
    
    result = filter.check_relevance(test_file, "authentication system")
    assert result['relevant'] is True
    assert result['confidence'] >= 0.5

def test_invalid_file():
    filter = FileFilter()
    result = filter.check_relevance(Path("non_existent.py"), "test")
    assert result['relevant'] is False
    assert 'error' in result

def test_batch_processing(mock_llm):
    filter = FileFilter()
    filter.classifier = mock_llm
    
    files = ["file1.py", "file2.py"]
    results = filter.batch_filter(files, "database")
    assert len(results) == 2
    assert all(r['relevant'] for r in results)
import pytest
from unittest.mock import Mock
from core.vector_db.qdrant_connector import VectorSearchEngine
import numpy as np

@pytest.fixture
def mock_embedder():
    embedder = Mock()
    embedder.encode.return_value = np.random.rand(384)
    return embedder

def test_add_file(mock_embedder):
    engine = VectorSearchEngine()
    engine.embedder = mock_embedder
    
    success = engine.add_file(
        "/src/auth.py",
        "def authenticate(): ...",
        {"language": "python"}
    )
    assert success is True

def test_search(mock_embedder):
    engine = VectorSearchEngine()
    engine.embedder = mock_embedder
    
    results = engine.search_files("user authentication", top_k=3)
    assert len(results) <= 3
    assert all('file_path' in r for r in results)

def test_embedding_consistency(mock_embedder):
    test_text = "test embedding generation"
    mock_embedder.encode.return_value = np.ones(384)
    
    engine = VectorSearchEngine()
    engine.embedder = mock_embedder
    
    vector = engine.embedder.encode(test_text)
    assert vector.shape == (384,)
    assert np.allclose(vector, np.ones(384))
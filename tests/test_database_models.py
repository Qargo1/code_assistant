import pytest
from core.database.models import FileMetadata, CodePatterns, SemanticType
from core.database.connection import get_session, init_db
from sqlalchemy.exc import IntegrityError

@pytest.fixture
def test_session():
    init_db()  # Создаем тестовые таблицы
    return get_session()

def test_create_file_metadata(test_session):
    test_file = FileMetadata(
        file_path="/src/auth.py",
        semantic_type=SemanticType.API,
        dependencies=["/src/database.py"],
        key_functions=["authenticate", "refresh_token"]
    )
    
    test_session.add(test_file)
    test_session.commit()
    
    result = test_session.query(FileMetadata).first()
    assert result.file_path == "/src/auth.py"
    assert result.semantic_type == SemanticType.API

def test_unique_file_path_constraint(test_session):
    file1 = FileMetadata(file_path="/src/main.py", semantic_type=SemanticType.CORE)
    test_session.add(file1)
    test_session.commit()
    
    file2 = FileMetadata(file_path="/src/main.py", semantic_type=SemanticType.UI)
    test_session.add(file2)
    
    with pytest.raises(IntegrityError):
        test_session.commit()
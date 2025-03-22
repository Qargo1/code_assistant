import pytest
import yaml
from pathlib import Path

def test_config_file_exists():
    """Проверка существования конфигурационного файла"""
    config_path = Path("config/base_config.yaml")
    assert config_path.exists(), "Config file not found"

def test_config_structure():
    """Проверка базовой структуры конфигурации"""
    with open("config/base_config.yaml") as f:
        config = yaml.safe_load(f)
    
    required_keys = ['project', 'database', 'logging', 'paths']
    for key in required_keys:
        assert key in config, f"Missing required config section: {key}"

def test_setup_dependencies():
    """Проверка наличия обязательных зависимостей"""
    with open("setup.py") as f:
        setup_content = f.read()
    
    required_packages = [
        'pyyaml',
        'python-dotenv',
        'psycopg2-binary'
    ]
    
    for pkg in required_packages:
        assert pkg in setup_content, f"Missing dependency: {pkg}"

def test_python_version():
    """Проверка версии Python"""
    import sys
    assert sys.version_info >= (3, 10), "Python 3.10 or newer required"

def test_postgres_connection():
    """Проверка подключения к PostgreSQL"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="your_password"
        )
        conn.close()
    except Exception as e:
        pytest.fail(f"PostgreSQL connection failed: {str(e)}")
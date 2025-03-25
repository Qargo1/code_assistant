import unittest
import os
import tempfile
from pathlib import Path
import sqlite3
from unittest.mock import patch, MagicMock

from tools.massive_code_parser import CSharpCodeParser, CodeDatabase

class TestCSharpParser(unittest.TestCase):
    """Тесты для анализатора C# кода, работающего с большими файлами"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        # Создаем временный файл для базы данных
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Пример небольшого C# кода для тестирования
        self.test_code = """
namespace TestProject
{
    public class User
    {
        public string Username { get; set; }
        public string Email { get; set; }
        
        public User(string username, string email)
        {
            Username = username;
            Email = email;
        }
        
        public bool IsValid()
        {
            return !string.IsNullOrEmpty(Username) && !string.IsNullOrEmpty(Email);
        }
    }
}
"""
        # Создаем временный файл с тестовым кодом
        self.temp_code_file = tempfile.NamedTemporaryFile(suffix='.cs', delete=False)
        with open(self.temp_code_file.name, 'w', encoding='utf-8') as f:
            f.write(self.test_code)
            
    def tearDown(self):
        """Очистка после завершения тестов"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        if os.path.exists(self.temp_code_file.name):
            os.unlink(self.temp_code_file.name)
    
    def test_database_initialization(self):
        """Тест инициализации базы данных"""
        db = CodeDatabase(self.temp_db.name)
        
        # Проверяем, что таблицы созданы
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        
        self.assertIn('files', tables)
        self.assertIn('classes', tables)
        self.assertIn('methods', tables)
        self.assertIn('dependencies', tables)
        
        conn.close()
        
    @patch('tools.massive_code_parser.CSharpCodeParser._init_roslyn')
    def test_simple_code_parsing(self, mock_init_roslyn):
        """Тест парсинга простого C# кода без реальной интеграции с Roslyn"""
        # Создаем мок-объект парсера с заглушкой для Roslyn
        parser = CSharpCodeParser()
        
        # Симулируем результаты парсинга
        # В реальной системе это бы делал Roslyn
        file_id = parser.db.add_file(
            self.temp_code_file.name,
            'csharp',
            len(self.test_code.splitlines())
        )
        
        class_id = parser.db.add_class(
            'User',
            file_id,
            'TestProject',
            3,
            22
        )
        
        parser.db.add_method(
            'IsValid',
            class_id,
            'bool',
            [],
            14,
            17,
            1
        )
        
        # Проверяем, что данные были добавлены в БД
        stats = parser.db.get_stats()
        self.assertEqual(stats['files'], 1)
        self.assertEqual(stats['classes'], 1)
        self.assertEqual(stats['methods'], 1)
        
    def test_content_chunking(self):
        """Тест разбивки содержимого файла на чанки"""
        from core.analysis.chunking import chunk_content
        
        chunks = chunk_content(self.test_code, self.temp_code_file.name)
        
        # Проверяем, что содержимое разбито корректно
        self.assertGreater(len(chunks), 0)
        self.assertIn('content', chunks[0])
        self.assertIn('metadata', chunks[0])
        
if __name__ == '__main__':
    unittest.main() 
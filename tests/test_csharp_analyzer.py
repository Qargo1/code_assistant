import unittest
import os
from pathlib import Path
import tempfile

from core.analysis.multilang_analyzer import MultiLanguageAnalyzer
from core.analysis.filter import FileFilter


class TestCSharpAnalyzer(unittest.TestCase):
    """Тесты для анализатора C# кода"""
    
    def setUp(self):
        """Настройка для тестов"""
        self.analyzer = MultiLanguageAnalyzer()
        self.filter = FileFilter()
        
        # Создаем временные файлы с C# кодом для тестирования
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csharp_sample = Path(self.temp_dir.name) / "Sample.cs"
        
        # Пример простого класса C#
        with open(self.csharp_sample, 'w') as f:
            f.write('''
using System;
namespace TestApp
{
    public class User
    {
        public int Id { get; set; }
        public string Name { get; set; }
        
        public User(int id, string name)
        {
            Id = id;
            Name = name;
        }
        
        public void DisplayInfo()
        {
            Console.WriteLine($"User {Id}: {Name}");
        }
    }
}
''')
    
    def tearDown(self):
        """Очистка после тестов"""
        self.temp_dir.cleanup()
    
    def test_csharp_file_detection(self):
        """Тест на определение C# файлов"""
        self.assertTrue(self.filter.is_csharp_file(str(self.csharp_sample)))
        
    def test_csharp_class_extraction(self):
        """Тест на извлечение классов из C# файла"""
        classes = self.analyzer.extract_classes(str(self.csharp_sample), language="csharp")
        self.assertIsNotNone(classes)
        self.assertIn("User", classes)
        
    def test_csharp_methods_extraction(self):
        """Тест на извлечение методов из C# файла"""
        methods = self.analyzer.extract_methods(str(self.csharp_sample), language="csharp")
        self.assertIsNotNone(methods)
        self.assertIn("DisplayInfo", methods)
        
    def test_csharp_properties_extraction(self):
        """Тест на извлечение свойств из C# файла"""
        properties = self.analyzer.extract_properties(str(self.csharp_sample), language="csharp")
        self.assertIsNotNone(properties)
        self.assertTrue(any("Id" in prop for prop in properties))
        self.assertTrue(any("Name" in prop for prop in properties))


if __name__ == '__main__':
    unittest.main() 
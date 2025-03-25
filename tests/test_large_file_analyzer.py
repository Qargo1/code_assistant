import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from core.analysis.chunking import CodeChunker
from core.analysis.multilang_analyzer import MultiLanguageAnalyzer


class TestLargeFileAnalyzer(unittest.TestCase):
    """Тесты для анализатора больших файлов кода"""
    
    def setUp(self):
        """Настройка для тестов"""
        self.analyzer = MultiLanguageAnalyzer()
        self.chunker = CodeChunker()
        
        # Создаем временные файлы для тестирования
        self.temp_dir = tempfile.TemporaryDirectory()
        self.large_csharp_file = Path(self.temp_dir.name) / "LargeFile.cs"
        
        # Генерируем большой C# файл с множеством классов и методов
        self._generate_large_csharp_file()
    
    def tearDown(self):
        """Очистка после тестов"""
        self.temp_dir.cleanup()
    
    def _generate_large_csharp_file(self):
        """
        Генерирует большой файл C# кода с множеством классов и методов
        для тестирования производительности и корректности анализа
        """
        with open(self.large_csharp_file, 'w') as f:
            f.write("using System;\nusing System.Collections.Generic;\nusing System.Linq;\n\n")
            f.write("namespace TestProject {\n\n")
            
            # Создаем 100 классов с методами и свойствами
            for i in range(100):
                f.write(f"    public class Class{i} {{\n")
                
                # Свойства
                f.write(f"        public int Id {{ get; set; }}\n")
                f.write(f"        public string Name {{ get; set; }}\n")
                
                # Конструктор
                f.write(f"        public Class{i}(int id, string name) {{\n")
                f.write(f"            Id = id;\n")
                f.write(f"            Name = name;\n")
                f.write(f"        }}\n\n")
                
                # Методы
                for j in range(5):
                    f.write(f"        public void Method{j}() {{\n")
                    f.write(f"            Console.WriteLine($\"Class{i}.Method{j} executed\");\n")
                    f.write(f"        }}\n\n")
                
                f.write("    }\n\n")
            
            f.write("}\n")
    
    def test_chunk_large_file(self):
        """Тест на разбиение большого файла на части"""
        chunks = self.chunker.chunk_file(str(self.large_csharp_file), max_chunk_size=1000)
        
        # Проверяем, что файл был разбит на части
        self.assertGreater(len(chunks), 1)
        
        # Проверяем, что размер каждого куска не превышает указанный
        for chunk in chunks:
            self.assertLessEqual(len(chunk.content), 1000)
    
    def test_extract_classes_from_large_file(self):
        """Тест на извлечение всех классов из большого файла"""
        classes = self.analyzer.extract_classes(str(self.large_csharp_file), language="csharp")
        
        # Проверяем, что извлечены все 100 классов
        self.assertEqual(len(classes), 100)
        
        # Проверяем наличие конкретных классов
        self.assertIn("Class0", classes)
        self.assertIn("Class50", classes)
        self.assertIn("Class99", classes)
    
    @patch('core.analysis.multilang_analyzer.MultiLanguageAnalyzer._read_file')
    def test_file_too_large_handling(self, mock_read):
        """Тест на корректную обработку слишком больших файлов"""
        # Имитируем файл размером более 10 МБ
        mock_read.return_value = "x" * (10 * 1024 * 1024 + 1)
        
        with self.assertLogs(level='WARNING'):
            # Должно выдать предупреждение о большом размере файла
            result = self.analyzer.analyze(str(self.large_csharp_file))
            
            # Проверяем, что анализ все равно выполнен
            self.assertIsNotNone(result)
            self.assertEqual(result["language"], "csharp")
    
    def test_performance_large_file(self):
        """Тест производительности анализа большого файла"""
        import time
        
        start_time = time.time()
        result = self.analyzer.analyze(str(self.large_csharp_file))
        end_time = time.time()
        
        # Анализ не должен занимать больше 5 секунд на локальном компьютере
        self.assertLess(end_time - start_time, 5.0)
        
        # Проверяем, что результат анализа содержит ожидаемые данные
        self.assertEqual(result["language"], "csharp")
        self.assertIn("classes", result)
        self.assertIn("methods", result)
        self.assertIn("properties", result)
        self.assertIn("namespaces", result)


if __name__ == '__main__':
    unittest.main() 
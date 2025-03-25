import unittest
import os
from pathlib import Path
import tempfile

from core.analysis.multilang_analyzer import MultiLanguageAnalyzer
from core.analysis.filter import FileFilter


class TestJavaAnalyzer(unittest.TestCase):
    """Тесты для анализатора Java кода"""
    
    def setUp(self):
        """Настройка для тестов"""
        self.analyzer = MultiLanguageAnalyzer()
        self.filter = FileFilter()
        
        # Создаем временные файлы с Java кодом для тестирования
        self.temp_dir = tempfile.TemporaryDirectory()
        self.java_sample = Path(self.temp_dir.name) / "User.java"
        
        # Пример простого класса Java
        with open(self.java_sample, 'w') as f:
            f.write('''
package com.test.app;

import java.util.Date;

/**
 * User class for storing user information
 */
public class User {
    private int id;
    private String name;
    private Date registrationDate;
    
    public User(int id, String name) {
        this.id = id;
        this.name = name;
        this.registrationDate = new Date();
    }
    
    public int getId() {
        return id;
    }
    
    public void setId(int id) {
        this.id = id;
    }
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public Date getRegistrationDate() {
        return registrationDate;
    }
    
    public void displayInfo() {
        System.out.println("User " + id + ": " + name);
    }
}
''')
    
    def tearDown(self):
        """Очистка после тестов"""
        self.temp_dir.cleanup()
    
    def test_java_file_detection(self):
        """Тест на определение Java файлов"""
        self.assertTrue(self.filter.is_java_file(str(self.java_sample)))
        
    def test_java_class_extraction(self):
        """Тест на извлечение классов из Java файла"""
        classes = self.analyzer.extract_classes(str(self.java_sample), language="java")
        self.assertIsNotNone(classes)
        self.assertIn("User", classes)
        
    def test_java_methods_extraction(self):
        """Тест на извлечение методов из Java файла"""
        methods = self.analyzer.extract_methods(str(self.java_sample), language="java")
        self.assertIsNotNone(methods)
        self.assertTrue(any("getId" in method for method in methods))
        self.assertTrue(any("setName" in method for method in methods))
        self.assertTrue(any("displayInfo" in method for method in methods))
        
    def test_java_fields_extraction(self):
        """Тест на извлечение полей из Java файла"""
        fields = self.analyzer.extract_fields(str(self.java_sample), language="java")
        self.assertIsNotNone(fields)
        self.assertTrue(any("id" in field for field in fields))
        self.assertTrue(any("name" in field for field in fields))
        self.assertTrue(any("registrationDate" in field for field in fields))
        
    def test_java_package_extraction(self):
        """Тест на извлечение информации о пакете из Java файла"""
        package = self.analyzer.extract_package(str(self.java_sample), language="java")
        self.assertEqual(package, "com.test.app")


if __name__ == '__main__':
    unittest.main() 
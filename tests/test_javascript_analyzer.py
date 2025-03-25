import unittest
import os
from pathlib import Path
import tempfile

from core.analysis.multilang_analyzer import MultiLanguageAnalyzer
from core.analysis.filter import FileFilter


class TestJavaScriptAnalyzer(unittest.TestCase):
    """Тесты для анализатора JavaScript кода"""
    
    def setUp(self):
        """Настройка для тестов"""
        self.analyzer = MultiLanguageAnalyzer()
        self.filter = FileFilter()
        
        # Создаем временные файлы с JavaScript кодом для тестирования
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Пример Javascript класса с использованием классов ES6
        self.js_class_sample = Path(self.temp_dir.name) / "UserClass.js"
        with open(self.js_class_sample, 'w') as f:
            f.write('''
/**
 * User class for managing user data
 */
class User {
  constructor(id, name) {
    this.id = id;
    this.name = name;
    this.createdAt = new Date();
  }
  
  /**
   * Get user information
   */
  getInfo() {
    return {
      id: this.id,
      name: this.name,
      createdAt: this.createdAt
    };
  }
  
  /**
   * Display user information
   */
  displayInfo() {
    console.log(`User ${this.id}: ${this.name}`);
  }
  
  /**
   * Static method to create admin user
   */
  static createAdmin(name) {
    return new User(0, `Admin: ${name}`);
  }
}

// Export the class
module.exports = User;
''')

        # Пример JavaScript кода с функциями
        self.js_function_sample = Path(self.temp_dir.name) / "functions.js"
        with open(self.js_function_sample, 'w') as f:
            f.write('''
/**
 * Utility functions for user management
 */

/**
 * Create a new user object
 */
function createUser(id, name) {
  return {
    id,
    name,
    createdAt: new Date()
  };
}

/**
 * Format user display name
 */
const formatDisplayName = (user) => {
  return `${user.name} (ID: ${user.id})`;
};

/**
 * Validate user data
 */
function validateUser(user) {
  if (!user.id || !user.name) {
    throw new Error('Invalid user data');
  }
  return true;
}

module.exports = {
  createUser,
  formatDisplayName,
  validateUser
};
''')
    
    def tearDown(self):
        """Очистка после тестов"""
        self.temp_dir.cleanup()
    
    def test_javascript_file_detection(self):
        """Тест на определение JavaScript файлов"""
        self.assertTrue(self.filter.is_javascript_file(str(self.js_class_sample)))
        self.assertTrue(self.filter.is_javascript_file(str(self.js_function_sample)))
        
    def test_javascript_class_extraction(self):
        """Тест на извлечение классов из JavaScript файла"""
        classes = self.analyzer.extract_classes(str(self.js_class_sample), language="javascript")
        self.assertIsNotNone(classes)
        self.assertIn("User", classes)
        
    def test_javascript_class_methods_extraction(self):
        """Тест на извлечение методов класса из JavaScript файла"""
        methods = self.analyzer.extract_methods(str(self.js_class_sample), language="javascript")
        self.assertIsNotNone(methods)
        self.assertTrue(any("getInfo" in method for method in methods))
        self.assertTrue(any("displayInfo" in method for method in methods))
        self.assertTrue(any("createAdmin" in method for method in methods))
        
    def test_javascript_functions_extraction(self):
        """Тест на извлечение функций из JavaScript файла"""
        functions = self.analyzer.extract_functions(str(self.js_function_sample), language="javascript")
        self.assertIsNotNone(functions)
        self.assertTrue(any("createUser" in func for func in functions))
        self.assertTrue(any("formatDisplayName" in func for func in functions))
        self.assertTrue(any("validateUser" in func for func in functions))
        
    def test_javascript_exports_extraction(self):
        """Тест на извлечение экспортов из JavaScript файла"""
        exports = self.analyzer.extract_exports(str(self.js_function_sample), language="javascript")
        self.assertIsNotNone(exports)
        self.assertTrue(any("createUser" in exp for exp in exports))
        self.assertTrue(any("formatDisplayName" in exp for exp in exports))
        self.assertTrue(any("validateUser" in exp for exp in exports))


if __name__ == '__main__':
    unittest.main() 
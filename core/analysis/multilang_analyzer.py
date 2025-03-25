# core/analysis/multilang_analyzer.py
from pathlib import Path
import re
import os
from typing import List, Dict, Any, Optional

class MultiLanguageAnalyzer:
    def __init__(self):
        self.language_extensions = {
            "csharp": [".cs"],
            "java": [".java"],
            "javascript": [".js", ".jsx", ".ts", ".tsx"]
        }
    
    def analyze(self, file_path: str) -> dict:
        """Анализирует файл и возвращает информацию о его структуре."""
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        ext = file_path.suffix.lower()
        
        # Определяем язык по расширению
        language = None
        for lang, extensions in self.language_extensions.items():
            if ext in extensions:
                language = lang
                break
        
        if not language:
            return {"error": "Unsupported file extension"}
        
        # Вызываем соответствующий анализатор
        result = {
            "language": language,
            "file_path": str(file_path),
            "classes": self.extract_classes(file_path, language),
            "methods": self.extract_methods(file_path, language),
        }
        
        # Добавляем специфичные для языка поля
        if language == "java":
            result["package"] = self.extract_package(file_path, language)
            result["fields"] = self.extract_fields(file_path, language)
        elif language == "csharp":
            result["properties"] = self.extract_properties(file_path, language)
            result["namespaces"] = self.extract_namespaces(file_path, language)
        elif language == "javascript":
            result["functions"] = self.extract_functions(file_path, language)
            result["exports"] = self.extract_exports(file_path, language)
            
        return result
        
    def extract_classes(self, file_path: str, language: str) -> List[str]:
        """Извлекает классы из файла указанного языка."""
        content = self._read_file(file_path)
        if not content:
            return []
            
        if language == "csharp":
            # Улучшенное регулярное выражение для C# классов
            pattern = r'class\s+(\w+)'
            matches = re.findall(pattern, content)
            return list(set(matches))
        elif language == "java":
            # Более точное регулярное выражение для Java классов
            pattern = r'(?:public|private|protected)\s+(?:abstract|final)?\s*class\s+(\w+)'
            matches = re.findall(pattern, content)
            return list(set(matches))
        elif language == "javascript":
            # ES6 классы в JavaScript
            pattern = r'class\s+(\w+)'
            matches = re.findall(pattern, content)
            return list(set(matches))
        
        return []
        
    def extract_methods(self, file_path: str, language: str) -> List[str]:
        """Извлекает методы из файла указанного языка."""
        content = self._read_file(file_path)
        if not content:
            return []
            
        if language == "csharp":
            # Улучшенное регулярное выражение для C# методов
            # Находим публичные методы без конструкторов
            pattern = r'(?:void|string|int|bool|\w+)\s+(\w+)\s*\([^\)]*\)\s*{'
            matches = re.findall(pattern, content)
            print(f"C# methods: {matches}")
            return list(set(matches))
        elif language == "java":
            # Находим имена методов в Java - более конкретное регулярное выражение
            print(f"Java content: {content[:200]}...")  # Выводим первые 200 символов для отладки
            # Улучшенное выражение для Java методов (включая геттеры/сеттеры)
            pattern = r'public\s+(?:(?:void|int|String|Date|boolean|double|float|long|short|byte|char|\w+(?:<.*?>)?))\s+(\w+)\s*\('
            matches = re.findall(pattern, content)
            print(f"Java methods: {matches}")
            
            # Удаляем конструкторы (имя совпадает с именем класса)
            classes = self.extract_classes(file_path, language)
            print(f"Java classes: {classes}")
            result = [method for method in matches if method not in classes]
            print(f"Java methods after filtering constructors: {result}")
            return result
        elif language == "javascript":
            # ES6 методы в JavaScript 
            class_methods = r'(?:async\s+)?(\w+)\s*\([^\)]*\)\s*{'
            matches = re.findall(class_methods, content)
            # Исключаем "constructor"
            methods = [m for m in matches if m != "constructor"]
            print(f"JavaScript methods: {methods}")
            return list(set(methods))
        
        return []
        
    def extract_properties(self, file_path: str, language: str) -> List[str]:
        """Извлекает свойства из файла C#."""
        if language != "csharp":
            return []
            
        content = self._read_file(file_path)
        if not content:
            return []
            
        # Простое регулярное выражение для C# свойств
        pattern = r'(?:public|private|protected|internal)?\s+\w+\s+(\w+)\s*\{\s*get\s*;'
        matches = re.findall(pattern, content)
        return list(set(matches))
        
    def extract_fields(self, file_path: str, language: str) -> List[str]:
        """Извлекает поля из файла Java."""
        if language != "java":
            return []
            
        content = self._read_file(file_path)
        if not content:
            return []
            
        # Исправленное регулярное выражение для Java полей
        pattern = r'private\s+(?:final|static)?\s*(?:int|String|Date|boolean|double|float|long|short|byte|char|\w+(?:<.*?>)?)\s+(\w+)'
        matches = re.findall(pattern, content)
        print(f"Java fields: {matches}")
        return list(set(matches))
        
    def extract_package(self, file_path: str, language: str) -> Optional[str]:
        """Извлекает имя пакета из файла Java."""
        if language != "java":
            return None
            
        content = self._read_file(file_path)
        if not content:
            return None
            
        # Паттерн для пакета Java
        pattern = r'package\s+([\w\.]+)\s*;'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        return None
        
    def extract_namespaces(self, file_path: str, language: str) -> List[str]:
        """Извлекает пространства имен из файла C#."""
        if language != "csharp":
            return []
            
        content = self._read_file(file_path)
        if not content:
            return []
            
        # Простое регулярное выражение для C# пространств имен
        pattern = r'namespace\s+([\w\.]+)'
        matches = re.findall(pattern, content)
        return list(set(matches))
        
    def extract_functions(self, file_path: str, language: str) -> List[str]:
        """Извлекает функции из JavaScript файла."""
        if language != "javascript":
            return []
            
        content = self._read_file(file_path)
        if not content:
            return []
            
        # Регулярные выражения для разных типов функций в JavaScript
        function_decl = r'function\s+(\w+)\s*\('
        const_func = r'const\s+(\w+)\s*=\s*(?:function|\([^\)]*\)\s*=>)'
        let_func = r'let\s+(\w+)\s*=\s*(?:function|\([^\)]*\)\s*=>)'
        var_func = r'var\s+(\w+)\s*=\s*(?:function|\([^\)]*\)\s*=>)'
        
        matches = []
        for pattern in [function_decl, const_func, let_func, var_func]:
            matches.extend(re.findall(pattern, content))
            
        return list(set(matches))
        
    def extract_exports(self, file_path: str, language: str) -> List[str]:
        """Извлекает экспортируемые элементы из JavaScript файла."""
        if language != "javascript":
            return []
            
        content = self._read_file(file_path)
        if not content:
            return []
            
        # CommonJS экспорты
        exports_pattern = r'module\.exports\s*=\s*{([^}]*)}'
        matches = re.findall(exports_pattern, content)
        
        if not matches:
            # Проверяем экспорт единственного класса/функции
            single_export = r'module\.exports\s*=\s*(\w+)'
            single_matches = re.findall(single_export, content)
            return single_matches
            
        exports = []
        for match in matches:
            # Извлекаем имена из списка экспортов
            items = match.split(',')
            for item in items:
                item = item.strip()
                if ':' in item:  # обрабатываем случай "name: value"
                    item = item.split(':')[0].strip()
                exports.append(item)
                
        return exports
    
    def _read_file(self, file_path: str) -> Optional[str]:
        """Читает содержимое файла."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
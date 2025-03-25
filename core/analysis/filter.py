"""
Модуль фильтрации файлов на основе их релевантности к запросу.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class FileFilter:
    """
    Класс для фильтрации файлов по их релевантности к запросу.
    Позволяет определить, какие файлы имеет смысл анализировать
    для конкретного запроса пользователя.
    """
    
    def __init__(self):
        """Инициализация фильтра файлов"""
        self.cache = {}
        self.ignored_extensions = {'.jpg', '.png', '.gif', '.dll', '.pdb', '.zip', '.exe', '.bin'}
        
        # Определяем расширения для разных языков
        self.csharp_extensions = {'.cs', '.csx'}
        self.java_extensions = {'.java'}
        self.javascript_extensions = {'.js', '.jsx', '.ts', '.tsx'}
        
        logger.info("FileFilter initialized")
    
    def check_relevance(self, file_path: Path, question: str) -> Dict[str, Any]:
        """
        Проверка релевантности файла к запросу.
        
        Args:
            file_path: Путь к файлу для проверки
            question: Текст запроса пользователя
            
        Returns:
            Словарь с информацией о релевантности
        """
        # Преобразование в Path, если передана строка
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        # Проверка расширения
        if file_path.suffix.lower() in self.ignored_extensions:
            return {"relevance": 0.0, "reason": "Ignored file extension"}
        
        # Базовая заглушка реализации
        # В реальной системе здесь будет сложная логика
        # с использованием эмбеддингов и семантического поиска
        return {
            "relevance": 0.8,  # Просто высокий вес по умолчанию
            "reason": "Stub implementation"
        }
    
    def _perform_analysis(self, file_path: Path, question: str) -> Dict:
        """
        Внутренний метод для анализа файла и определения его релевантности.
        В реальной системе будет использовать векторную близость между
        содержимым файла и запросом.
        
        Args:
            file_path: Путь к файлу
            question: Текст запроса
            
        Returns:
            Словарь с результатами анализа
        """
        # Это заглушка для метода
        # В реальной системе здесь будет сложный анализ
        return {
            "relevance": 0.8,
            "file_path": str(file_path),
            "question": question
        }
        
    def is_csharp_file(self, file_path: str) -> bool:
        """
        Проверяет, является ли файл C# кодом.
        
        Args:
            file_path: Путь к файлу для проверки
            
        Returns:
            True, если файл содержит C# код, иначе False
        """
        if isinstance(file_path, Path):
            file_path = str(file_path)
            
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.csharp_extensions
        
    def is_java_file(self, file_path: str) -> bool:
        """
        Проверяет, является ли файл Java кодом.
        
        Args:
            file_path: Путь к файлу для проверки
            
        Returns:
            True, если файл содержит Java код, иначе False
        """
        if isinstance(file_path, Path):
            file_path = str(file_path)
            
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.java_extensions
        
    def is_javascript_file(self, file_path: str) -> bool:
        """
        Проверяет, является ли файл JavaScript/TypeScript кодом.
        
        Args:
            file_path: Путь к файлу для проверки
            
        Returns:
            True, если файл содержит JavaScript/TypeScript код, иначе False
        """
        if isinstance(file_path, Path):
            file_path = str(file_path)
            
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.javascript_extensions
        
    def filter_by_language(self, files: List[str], language: str) -> List[str]:
        """
        Фильтрует список файлов по указанному языку.
        
        Args:
            files: Список путей к файлам
            language: Язык для фильтрации ('csharp', 'java', 'javascript')
            
        Returns:
            Отфильтрованный список файлов
        """
        if language == 'csharp':
            return [f for f in files if self.is_csharp_file(f)]
        elif language == 'java':
            return [f for f in files if self.is_java_file(f)]
        elif language == 'javascript':
            return [f for f in files if self.is_javascript_file(f)]
        else:
            return files  # Если язык не определен, возвращаем все файлы
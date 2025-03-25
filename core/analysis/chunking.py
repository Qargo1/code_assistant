"""
Модуль для разбиения содержимого файлов на логические чанки.
"""

import logging
import re
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CodeChunk:
    """Класс для представления чанка кода с метаданными"""
    content: str
    file_path: Optional[str] = None
    chunk_id: Optional[str] = None
    start_pos: int = 0
    end_pos: Optional[int] = None
    chunk_type: str = "raw"
    metadata: Optional[Dict[str, Any]] = None

class CodeChunker:
    """
    Класс для разбиения кода на чанки разными способами.
    Позволяет обрабатывать большие файлы и оптимизировать
    их для анализа и векторизации.
    """
    
    def __init__(self):
        """Инициализация разбивателя кода на чанки"""
        logger.info("CodeChunker initialized")
    
    def chunk_file(self, file_path: str, max_chunk_size: int = 1500, overlap: int = 200) -> List[CodeChunk]:
        """
        Разбивает файл на чанки с указанным перекрытием.
        
        Args:
            file_path: Путь к файлу
            max_chunk_size: Максимальный размер чанка в символах
            overlap: Размер перекрытия между соседними чанками
            
        Returns:
            Список объектов CodeChunk
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []
            
        # Используем существующую функцию для разбиения содержимого
        chunks_data = chunk_content(content, file_path, max_chunk_size, overlap)
        
        # Преобразуем словари в объекты CodeChunk
        chunks = []
        for chunk_data in chunks_data:
            chunk = CodeChunk(
                content=chunk_data["content"],
                file_path=file_path,
                chunk_id=str(chunk_data["metadata"]["chunk_id"]),
                start_pos=chunk_data["metadata"].get("start_pos", 0),
                end_pos=chunk_data["metadata"].get("end_pos"),
                chunk_type=chunk_data["metadata"]["chunk_type"],
                metadata=chunk_data["metadata"]
            )
            chunks.append(chunk)
            
        return chunks
    
    def chunk_file_by_function(self, file_path: str) -> List[CodeChunk]:
        """
        Разбивает файл на чанки по границам функций/методов.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Список объектов CodeChunk
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []
            
        # Используем существующую функцию для разбиения по функциям
        chunks_data = chunk_by_function(content, file_path)
        
        # Преобразуем словари в объекты CodeChunk
        chunks = []
        for chunk_data in chunks_data:
            chunk = CodeChunk(
                content=chunk_data["content"],
                file_path=file_path,
                chunk_id=str(chunk_data["metadata"].get("chunk_id", "unknown")),
                chunk_type=chunk_data["metadata"]["chunk_type"],
                metadata=chunk_data["metadata"]
            )
            chunks.append(chunk)
            
        return chunks
    
    def chunk_directory(self, directory_path: str, max_chunk_size: int = 1500, 
                        include_extensions: Optional[List[str]] = None) -> Dict[str, List[CodeChunk]]:
        """
        Разбивает все файлы в указанной директории на чанки.
        
        Args:
            directory_path: Путь к директории
            max_chunk_size: Максимальный размер чанка
            include_extensions: Список расширений файлов для обработки (если None, обрабатываются все)
            
        Returns:
            Словарь с путями к файлам и списками чанков
        """
        result = {}
        
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            logger.error(f"Directory {directory_path} does not exist or is not a directory")
            return result
            
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Если указаны расширения для включения, проверяем их
                if include_extensions:
                    ext = os.path.splitext(file)[1].lower()
                    if ext not in include_extensions:
                        continue
                
                # Пропускаем очень большие файлы (>10MB) или нетекстовые
                if not self._is_valid_text_file(file_path):
                    continue
                    
                chunks = self.chunk_file(file_path, max_chunk_size)
                if chunks:
                    result[file_path] = chunks
                    
        return result
    
    def _is_valid_text_file(self, file_path: str, max_size_mb: int = 10) -> bool:
        """
        Проверяет, является ли файл текстовым и не превышает ли максимальный размер.
        
        Args:
            file_path: Путь к файлу
            max_size_mb: Максимальный размер файла в МБ
            
        Returns:
            True, если файл подходит для обработки
        """
        # Проверка размера
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > max_size_mb:
                logger.warning(f"File {file_path} is too large ({size_mb:.2f} MB > {max_size_mb} MB)")
                return False
                
            # Пробуем открыть файл как текстовый
            with open(file_path, 'r', encoding='utf-8') as f:
                # Читаем небольшой фрагмент, чтобы проверить, что это текст
                f.read(1024)
                return True
        except UnicodeDecodeError:
            logger.debug(f"File {file_path} is not a text file (UnicodeDecodeError)")
            return False
        except Exception as e:
            logger.debug(f"Error checking file {file_path}: {e}")
            return False

def chunk_content(
    content: str,
    file_path: Optional[str] = None,
    chunk_size: int = 1500,
    overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Разбивает содержимое файла на чанки с возможностью перекрытия.
    
    Args:
        content: Содержимое файла для разбиения
        file_path: Путь к файлу (опционально, для метаданных)
        chunk_size: Максимальный размер чанка в символах
        overlap: Размер перекрытия между соседними чанками
        
    Returns:
        Список словарей, каждый из которых содержит чанк и его метаданные
    """
    logger.debug(f"Chunking file: {file_path}, size: {len(content)}")
    
    # Для демонстрации используем простую логику разбиения 
    # по размеру с учетом перекрытия
    chunks = []
    
    # Если файл очень маленький, возвращаем его целиком
    if len(content) <= chunk_size:
        return [{
            "content": content,
            "metadata": {
                "file_path": file_path,
                "chunk_id": 0,
                "total_chunks": 1,
                "chunk_type": "full_file"
            }
        }]
    
    # Разбиение на чанки с перекрытием
    position = 0
    chunk_id = 0
    
    while position < len(content):
        chunk_end = min(position + chunk_size, len(content))
        
        # Получаем текущий чанк
        current_chunk = content[position:chunk_end]
        
        # Добавляем чанк в результат
        chunks.append({
            "content": current_chunk,
            "metadata": {
                "file_path": file_path,
                "chunk_id": chunk_id,
                "start_pos": position,
                "end_pos": chunk_end,
                "chunk_type": "raw"
            }
        })
        
        # Перемещаем позицию с учетом перекрытия
        position = chunk_end - overlap if chunk_end < len(content) else len(content)
        chunk_id += 1
    
    # Обновление метаданных с общим количеством чанков
    for chunk in chunks:
        chunk["metadata"]["total_chunks"] = len(chunks)
    
    return chunks


def chunk_by_function(content: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Разбивает содержимое файла на чанки по функциям или методам.
    Этот метод использует регулярные выражения для поиска определений функций
    в различных языках программирования.
    
    Args:
        content: Содержимое файла
        file_path: Путь к файлу для определения языка
        
    Returns:
        Список чанков с метаданными
    """
    # Заглушка метода
    # В реальной системе здесь будет сложный парсинг кода
    chunks = []
    
    # Определяем язык на основе расширения файла
    extension = Path(file_path).suffix.lower()
    
    # Простой пример для Python файлов
    if extension == '.py':
        # Очень простой паттерн для определения функций в Python
        function_pattern = r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*?\):"
        matches = re.finditer(function_pattern, content, re.DOTALL)
        
        prev_end = 0
        function_id = 0
        
        for match in matches:
            start = match.start()
            
            # Если есть некоторый текст перед первой функцией, добавляем его как отдельный чанк
            if function_id == 0 and start > 0:
                chunks.append({
                    "content": content[:start],
                    "metadata": {
                        "file_path": file_path,
                        "chunk_id": "header",
                        "chunk_type": "header"
                    }
                })
            
            # Ищем конец функции (примерно - до следующей функции или конца файла)
            next_match = re.search(function_pattern, content[start + 1:], re.DOTALL)
            if next_match:
                end = start + 1 + next_match.start()
            else:
                end = len(content)
            
            # Добавляем функцию как чанк
            chunks.append({
                "content": content[start:end],
                "metadata": {
                    "file_path": file_path,
                    "chunk_id": f"func_{function_id}",
                    "function_name": match.group(1),
                    "chunk_type": "function"
                }
            })
            
            prev_end = end
            function_id += 1
    
    # Если чанки не получилось извлечь, возвращаем один чанк со всем содержимым
    if not chunks:
        return chunk_content(content, file_path)
    
    return chunks 
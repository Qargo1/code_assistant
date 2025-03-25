"""
Модуль анализа кода для системы Code Assistant.
Содержит инструменты для фильтрации, чанкинга и обработки кода.
"""

from core.analysis.filter import FileFilter
from core.analysis.chunking import chunk_content

__all__ = ['FileFilter', 'chunk_content']

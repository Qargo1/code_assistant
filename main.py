"""
main.py - Главный модуль Code Assistant
"""

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

# Стандартные библиотеки
import zlib
from dotenv import load_dotenv
import os

# Сторонние зависимости
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, MatchAny
from diskcache import Cache
from tqdm import tqdm
from ollama import chat
import textwrap

# Внутренние модули
from core.cache import (
    LayeredCache,
    RedisCache,
    FileSystemCache,
    CompressedCache
)
from core.analysis import FileFilter, chunk_content
from core.automation import PriorityAnalysisQueue
from core.vector_db import VectorSearchEngine
from core.database import init_db, get_session, FileMetadata, SemanticType
from interfaces.telegram import CodeAssistantBot
from utils.monitoring import CodebaseMetrics
from config import settings

from bridges.java_terminal import JavaTerminalBridge
from bridges.csharp_db import CSharpDBBridge
from bridges.js_scraper import JSScraper


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnhancedFileSystemCache(FileSystemCache):
    def cleanup(self, max_size: int = settings.CACHE_MAX_SIZE) -> None:
        """Очистка кэша с сохранением последних файлов"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*'))
            if total_size > max_size:
                files = sorted(
                    self.cache_dir.rglob('*'),
                    key=lambda f: f.stat().st_mtime
                )
                for f in files[:-settings.CACHE_KEEP_FILES]:
                    try:
                        f.unlink()
                    except Exception as e:
                        logger.error(f"Error deleting {f}: {str(e)}")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {str(e)}")


class SafeCompressedCache(CompressedCache):
    def get(self, key: str) -> Optional[bytes]:
        """Безопасное получение сжатых данных"""
        try:
            compressed = self.backend.get(key)
            return zlib.decompress(compressed) if compressed else None
        except zlib.error as e:
            logger.error(f"Decompression error: {str(e)}")
            return None


class OptimizedFileFilter(FileFilter):
    def __init__(self):
        super().__init__()
        self.cache.add_backend(SafeCompressedCache(RedisCache()))
        
    def check_relevance(self, file_path: Path, question: str) -> Dict:
        """Проверка релевантности с улучшенным кэшированием"""
        cache_key = f"{file_path.resolve()}-{question}"
        try:
            if cached := self.cache.get(cache_key):
                return json.loads(cached)
                
            # Основная логика анализа
            result = self._perform_analysis(file_path, question)
            
            self.cache.set(
                cache_key,
                json.dumps(result),
                timedelta(hours=settings.CACHE_TTL_HOURS)
            )
            return result
        except Exception as e:
            logger.error(f"Analysis failed for {file_path}: {str(e)}")
            return {"error": str(e)}


class AdvancedVectorSearch(VectorSearchEngine):
    def add_batch(self, files: List[Tuple[str, str, dict]]) -> None:
        """Пакетное добавление с прогресс-баром"""
        with ThreadPoolExecutor() as executor:
            list(tqdm(
                executor.map(self._safe_add_file, files),
                total=len(files),
                desc="Indexing files"
            ))
            
    def _safe_add_file(self, file_data: Tuple[str, str, dict]) -> None:
        """Безопасное добавление файла с обработкой ошибок"""
        try:
            self.add_file(*file_data)
        except Exception as e:
            logger.error(f"Failed to add {file_data[0]}: {str(e)}")


class IntelligentChatBot:
    def __init__(self):
        self._init_components()
        self._load_data()
        
    def _init_components(self):
        """Инициализация компонентов системы"""
        self.qa_system = QdrantCodeSearch(settings.MERGED_FILE_PATH)
        self.messages = []
        self.context_template = textwrap.dedent(settings.CONTEXT_TEMPLATE)
        
    def _load_data(self):
        """Загрузка и индексация данных"""
        try:
            self.qa_system.load_and_index_data()
        except Exception as e:
            logger.critical(f"Initialization failed: {str(e)}")
            raise RuntimeError("Failed to initialize QA system") from e

    def _format_response(self, results: List[dict]) -> str:
        """Форматирование контекста для ответа"""
        context = []
        langs = set()
        
        for res in results:
            langs.add(res['lang'])
            context.append(
                f"🔍 **Code Fragment** (Score: {res['score']:.2f}, Lines {res['start_line']}-{res['end_line']})\n"
                f"```{res['lang']}\n{textwrap.shorten(res['text'], width=200)}\n```\n"
                f"📁 Source: {res['source']}"
            )
            
        return self.context_template.format(
            context='\n\n'.join(context),
            langs=", ".join(langs)
            
    def process_query(self, query: str) -> str:
        """Обработка пользовательского запроса"""
        try:
            context = self._get_context(query)
            return self._generate_answer(context, query)
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            return settings.ERROR_MESSAGE

def main():
    """Основная функция инициализации и запуска"""
    try:
        # Инициализация системных компонентов
        load_dotenv()
        init_db()
        
        # Запуск Telegram бота
        bot = CodeAssistantBot(os.getenv("TELEGRAM_TOKEN"))
        bot.run()
        
        # Инициализация векторной базы
        vector_engine = AdvancedVectorSearch()
        vector_engine.init_embedder()
        
        # Пример использования
        with open("src/auth.py") as f:
            content = f.read()
            vector_engine.add_file("src/auth.py", content, {"type": "authentication"})
            
        results = vector_engine.hybrid_search(
            "How to implement user login?",
            ["auth", "security"],
            top_k=5
        )
        
        for result in results:
            logger.info(f"Found: {result['file_path']} ({result['score']:.2f})")
            
    except Exception as e:
        logger.critical(f"System startup failed: {str(e)}")
        raise
        
        
class CodeAssistant:
    def __init__(self):
        self.terminal = JavaTerminalBridge()
        self.database = CSharpDBBridge()
        self.scraper = JSScraper()
    
    def handle_command(self, user_input: str):
        if user_input.startswith("terminal:"):
            cmd = user_input.split(":", 1)[1]
            return self.terminal.run_command(cmd)
        
        elif user_input.startswith("query:"):
            sql = user_input.split(":", 1)[1]
            return self.database.execute_query(sql)
        
        elif user_input.startswith("scrape:"):
            url, selector = user_input.split(":", 1)[1].split(" ", 1)
            return self.scraper.scrape(url, selector)
        

if __name__ == "__main__":
    main()
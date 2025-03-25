"""
Code Assistant - Интеллектуальный помощник для анализа большого C# проекта

Основной файл запуска системы, объединяющий:
1. Парсинг C# кода с использованием Roslyn
2. Векторное хранилище для семантического поиска кода
3. Телеграм-бот для взаимодействия с пользователем
4. Механизмы кэширования и оптимизации запросов
5. Многоязычную поддержку (C#, Python, Java, JS)
6. Автоматизацию и интеграцию с внешними сервисами
"""

import os
import logging
import json
import argparse
import zlib
import threading
import queue
from pathlib import Path
from datetime import datetime, timedelta
import textwrap
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Подключение компонентов для работы с векторами
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, MatchAny
from ollama import chat, embed
from diskcache import Cache
from tqdm import tqdm

# Импорт наших модулей
from utils.semantic import QdrantCodeSearch
from utils.embeddings import EmbeddingService
from utils.db_manager import CodeKnowledgeDB
from utils.resource_monitor import CodebaseMetrics

from tools.massive_code_parser import CSharpCodeParser
from tools.vector_embedding_manager import EmbeddingManager, CodeEmbedder

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

from bridges.java_terminal import JavaTerminalBridge
from bridges.csharp_db import CSharpDBBridge
from bridges.js_scraper import JSScraper

from interfaces.telegram import CodeAssistantBot

# Настройка логирования
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
CONFIG = {
    "merged_file_path": "C:/Users/korda/YandexDisk/steelf/SteelF/merged_code.txt",
    "ollama_model": "qwen2.5-coder:3b",
    "embedding_model": "nomic-embed-text",
    "telegram_token": None,  # Загружается из .env
    "cache_dir": "data/cache",
    "vector_storage": "qdrant_storage",
    "db_path": "data/code_knowledge.db",
    "parallel_processes": 4,
    "cache_max_size": 1024 * 1024 * 100,  # 100 MB
    "cache_keep_files": 50,
    "cache_ttl_hours": 24,
    "error_message": "⚠️ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз."
}

# Система промптов
CONTEXT_TEMPLATE = """
**Code Context**
{context}

**Question**
{question}

**Answer Guidelines**
1. Be specific about code implementation
2. Reference relevant code sections
3. Provide examples when possible
4. Consider language-specific features ({langs})
"""

SEARCH_PROMPT = """
На основании кода и вопроса, определите:
1. Какие части кода наиболее релевантны для ответа?
2. Какие классы и методы нужно исследовать?
3. Какие взаимосвязи важны в контексте вопроса?

Код: {code}
Вопрос: {question}
"""

# Расширенные классы кэширования
class EnhancedFileSystemCache(FileSystemCache):
    def cleanup(self, max_size: int = CONFIG["cache_max_size"]) -> None:
        """Очистка кэша с сохранением последних файлов"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*'))
            if total_size > max_size:
                files = sorted(
                    self.cache_dir.rglob('*'),
                    key=lambda f: f.stat().st_mtime
                )
                for f in files[:-CONFIG["cache_keep_files"]]:
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
                timedelta(hours=CONFIG["cache_ttl_hours"])
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


class CodeAssistant:
    """Основной класс системы анализа кода"""
    
    def __init__(self, config=None):
        """Инициализация компонентов системы"""
        self.config = config or CONFIG
        self.messages = []
        self._ensure_dirs()
        
        # Инициализация Bridges для внешних сервисов
        try:
            self.terminal = JavaTerminalBridge()
            self.database = CSharpDBBridge()
            self.scraper = JSScraper()
            logger.info("External service bridges initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize bridges: {str(e)}")
        
        # Инициализация векторного поиска
        self.qa_system = QdrantCodeSearch(self.config["merged_file_path"])
        try:
            self.qa_system.load_and_index_data()
            logger.info("Vector search system initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing QA system: {str(e)}")
            raise
        
        # Инициализация эмбеддингов
        self.embedding_manager = EmbeddingManager()
        self.code_embedder = CodeEmbedder(self.embedding_manager)
        
        # Инициализация расширенного векторного поиска
        self.vector_engine = AdvancedVectorSearch()
        self.vector_engine.init_embedder()
        
        # Настройка кэширования
        self.cache = {}
        self._last_clean = datetime.now()
        
        # Инициализация БД
        try:
            init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
        
    def _ensure_dirs(self):
        """Создание необходимых директорий"""
        os.makedirs("logs", exist_ok=True)
        os.makedirs(self.config["cache_dir"], exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("qdrant_storage", exist_ok=True)
        
    def _update_history(self, role, content):
        """Обновление истории сообщений"""
        self.messages.append({'role': role, 'content': content})
        # Ограничение истории последними 10 сообщениями
        if len(self.messages) > 10:
            self.messages = self.messages[-10:]
        
        # Очистка кэша раз в час
        if (datetime.now() - self._last_clean).total_seconds() > 3600:
            self._clean_cache()
    
    def _clean_cache(self):
        """Очистка устаревших записей кэша"""
        current_time = datetime.now()
        keys_to_remove = []
        
        for key, (value, timestamp) in self.cache.items():
            if (current_time - timestamp).total_seconds() > 86400:  # 24 часа
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.cache[key]
            
        self._last_clean = current_time
        logger.info(f"Cache cleaned: removed {len(keys_to_remove)} items")
    
    def _format_context(self, results):
        """Форматирование контекста из найденных фрагментов кода"""
        context = []
        langs = set()
        
        for res in results:
            langs.add(res['lang'])
            context.append(
                f"🔍 **Code Fragment** (Score: {res['score']:.2f}, Lines {res.get('start_line', '?')}-{res.get('end_line', '?')})\n"
                f"```{res['lang']}\n{textwrap.shorten(res['text'], width=200)}\n```\n"
                f"📁 Source: {res.get('source', 'Unknown')}"
            )
            
        return '\n\n'.join(context), langs
    
    def get_context(self, query):
        """Получение контекста для запроса"""
        # Проверка кэша
        cache_key = f"context_{query}"
        if cache_key in self.cache:
            logger.info(f"Cache hit for query: {query}")
            return self.cache[cache_key][0]
        
        # Поиск релевантного кода
        results = self.qa_system.search_code(query, top_k=5)
        context, langs = self._format_context(results)
        
        # Форматирование контекста
        formatted_context = CONTEXT_TEMPLATE.format(
            context=context,
            question=query,
            langs=", ".join(langs)
        )
        
        # Сохранение в кэш
        self.cache[cache_key] = (formatted_context, datetime.now())
        return formatted_context
    
    def ask(self, query):
        """Обработка пользовательского запроса"""
        try:
            # Получение контекста
            context = self.get_context(query)
            self._update_history('user', query)
            
            # Запрос к LLM
            response = chat(
                model=self.config["ollama_model"],
                messages=[{
                    "role": "system",
                    "content": "You are a senior software engineer helping with C# code analysis."
                }] + self.messages[-5:] + [{
                    "role": "user",
                    "content": context
                }]
            )
            
            answer = response['message']['content']
            self._update_history('assistant', answer)
            return answer
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"⚠️ Произошла ошибка при обработке запроса: {str(e)}"
    
    def process_file(self, file_path):
        """Обработка отдельного файла C#"""
        try:
            parser = CSharpCodeParser()
            result = parser.analyze_file(file_path)
            return result
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return {"error": str(e)}
    
    def analyze_project(self, merged_file_path=None):
        """Полный анализ проекта на C#"""
        try:
            # Используем переданный путь или из конфигурации
            file_path = merged_file_path or self.config["merged_file_path"]
            
            logger.info(f"Starting project analysis: {file_path}")
            
            # Запуск парсера C# кода
            parser = CSharpCodeParser()
            parser.parse_merged_file(file_path)
            
            # Вывод результатов
            stats = parser.db.get_stats()
            logger.info(f"Analysis completed: {stats}")
            
            return {
                "status": "success",
                "stats": stats,
                "message": "Проект успешно проанализирован"
            }
            
        except Exception as e:
            logger.error(f"Project analysis failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Ошибка анализа проекта: {str(e)}"
            }
    
    def handle_command(self, user_input: str):
        """Обработка специальных команд"""
        try:
            if user_input.startswith("terminal:"):
                cmd = user_input.split(":", 1)[1]
                return self.terminal.run_command(cmd)
            
            elif user_input.startswith("query:"):
                sql = user_input.split(":", 1)[1]
                return self.database.execute_query(sql)
            
            elif user_input.startswith("scrape:"):
                url, selector = user_input.split(":", 1)[1].split(" ", 1)
                return self.scraper.scrape(url, selector)
            
            # Обычный запрос к LLM
            return self.ask(user_input)
        
        except Exception as e:
            logger.error(f"Command handling failed: {str(e)}")
            return CONFIG["error_message"]
    
    def get_system_status(self):
        """Получение статуса системы"""
        return {
            "vector_db_size": self.vector_engine.client.get_collection().vectors_count,
            "last_error": self._get_last_error(),
            "memory_usage": CodebaseMetrics.get_memory_usage(),
            "cache_size": sum(f.stat().st_size for f in Path(self.config["cache_dir"]).rglob('*')),
            "uptime": (datetime.now() - self._start_time).total_seconds() // 60  # в минутах
        }
    
    def _get_last_error(self):
        """Получение последней ошибки из журнала"""
        try:
            with open("logs/error.log", "r") as f:
                lines = f.readlines()
                return lines[-1].strip() if lines else "No errors"
        except Exception:
            return "Error log not available"
    
    def chat(self):
        """Интерактивный режим в консоли"""
        print("🚀 Code Assistant - Интеллектуальный помощник для C#\n")
        print("Введите 'exit' для выхода, 'analyze' для анализа проекта\n")
        
        while True:
            try:
                user_input = input("👤 Вопрос: ")
                if user_input.lower() == 'exit':
                    break
                elif user_input.lower() == 'analyze':
                    result = self.analyze_project()
                    print(f"📊 {result['message']}")
                    if result['status'] == 'success':
                        print(f"📈 Статистика: {result['stats']}")
                else:
                    print("🤖 Обработка запроса...")
                    response = self.handle_command(user_input)
                    print(f"🤖 Ответ: {response}")
            except KeyboardInterrupt:
                print("\nВыход из программы...")
                break
            except Exception as e:
                print(f"⚠️ Ошибка: {str(e)}")


class TelegramBot:
    """Telegram-бот для взаимодействия с системой"""
    
    def __init__(self, token, code_assistant):
        """Инициализация Telegram бота"""
        from telegram import Update
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
        
        self.token = token
        self.code_assistant = code_assistant
        self.application = ApplicationBuilder().token(self.token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков сообщений"""
        from telegram.ext import CommandHandler, MessageHandler, filters
        
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("analyze", self.analyze))
        self.application.add_handler(CommandHandler("status", self.handle_status))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
    async def start(self, update, _):
        """Обработчик команды /start"""
        await update.message.reply_text(
            "👋 Привет! Я Code Assistant - интеллектуальный помощник для анализа C# кода.\n\n"
            "Задайте мне вопрос о вашем коде, и я постараюсь помочь!\n"
            "Используйте /help для получения справки."
        )
    
    async def help(self, update, _):
        """Обработчик команды /help"""
        help_text = (
            "🔍 *Команды бота:*\n\n"
            "• Просто напишите вопрос о коде\n"
            "• /analyze - анализ всего проекта\n"
            "• /status - статус системы\n"
            "• /help - эта справка\n\n"
            "*Специальные команды:*\n"
            "• terminal:your_command - выполнить команду в терминале\n"
            "• query:SQL_query - выполнить SQL-запрос\n"
            "• scrape:url selector - получить данные с веб-страницы"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
        
    async def analyze(self, update, _):
        """Обработчик команды /analyze"""
        await update.message.reply_text("🔍 Запускаю анализ проекта. Это может занять некоторое время...")
        
        def run_analysis():
            try:
                result = self.code_assistant.analyze_project()
                return result
            except Exception as e:
                logger.error(f"Analysis failed: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Ошибка анализа: {str(e)}"
                }
        
        # Запуск анализа в отдельном потоке
        thread = threading.Thread(target=run_analysis)
        thread.start()
        thread.join()
        
        # Отправка результата
        result = run_analysis()
        if result["status"] == "success":
            await update.message.reply_text(
                f"✅ {result['message']}\n\n"
                f"📊 Статистика:\n"
                f"• Классов: {result['stats'].get('classes', 0)}\n"
                f"• Методов: {result['stats'].get('methods', 0)}\n"
                f"• Файлов: {result['stats'].get('files', 0)}"
            )
        else:
            await update.message.reply_text(f"❌ {result['message']}")
    
    async def handle_status(self, update, _):
        """Обработчик команды /status"""
        status = self.code_assistant.get_system_status()
        status_text = (
            f"🖥 System Status:\n"
            f"• Vector DB size: {status['vector_db_size']}\n"
            f"• Cache size: {status['cache_size'] // 1024} KB\n"
            f"• Memory usage: {status['memory_usage']} MB\n"
            f"• Uptime: {status['uptime']} minutes\n"
            f"• Last error: {status['last_error']}"
        )
        await update.message.reply_text(status_text)
            
    async def handle_message(self, update, _):
        """Обработка обычных сообщений"""
        await update.message.reply_text("🤖 Обрабатываю ваш запрос...")
        
        try:
            user_message = update.message.text
            logger.info(f"Received message: {user_message}")
            
            # Запуск обработки в отдельном потоке
            response_queue = queue.Queue()
            
            def process():
                try:
                    result = self.code_assistant.handle_command(user_message)
                    response_queue.put(result)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    response_queue.put(f"⚠️ Произошла ошибка: {str(e)}")
            
            thread = threading.Thread(target=process)
            thread.start()
            thread.join()
            
            # Получение и отправка ответа
            response = response_queue.get()
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Message handling failed: {str(e)}")
            await update.message.reply_text(f"⚠️ Ошибка обработки сообщения: {str(e)}")
    
    def run(self):
        """Запуск бота"""
        logger.info("Starting Telegram bot")
        self.application.run_polling()


def main():
    """Основная функция запуска приложения"""
    parser = argparse.ArgumentParser(description="Code Assistant - AI-powered code analysis system")
    parser.add_argument("--console", action="store_true", help="Run in console mode")
    parser.add_argument("--analyze", type=str, help="Path to merged code file for analysis")
    parser.add_argument("--telegram", action="store_true", help="Run Telegram bot")
    args = parser.parse_args()

    try:
        # Загрузка переменных окружения
        load_dotenv()
        CONFIG["telegram_token"] = os.getenv("TELEGRAM_TOKEN")
        
        # Инициализация системы
        code_assistant = CodeAssistant()
        
        # Обработка аргументов командной строки
        if args.analyze:
            result = code_assistant.analyze_project(args.analyze)
            print(f"📊 {result['message']}")
            if result['status'] == 'success':
                print(f"📈 Статистика: {result['stats']}")
        elif args.telegram:
            if not CONFIG["telegram_token"]:
                print("⚠️ Telegram token not found. Please set TELEGRAM_TOKEN in .env file.")
                return
            bot = TelegramBot(CONFIG["telegram_token"], code_assistant)
            bot.run()
        elif args.console:
            code_assistant.chat()
        else:
            code_assistant.chat()  # По умолчанию запускаем консольный режим
            
    except Exception as e:
        logger.critical(f"Application startup failed: {str(e)}")
        print(f"⚠️ Critical error: {str(e)}")
        raise


if __name__ == "__main__":
    main() 
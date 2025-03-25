"""
telegram_code_assistant.py - Телеграм бот для работы с кодом

Модуль реализует Telegram-бот для работы с базой кода C#,
автоматического поиска и анализа кода, а также запуска
команд для анализа и работы с моделью LLM.
"""

import os
import re
import time
import json
import logging
import subprocess
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
from datetime import datetime

# Импорт Telegram API
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes, 
    filters
)

# Импорт для работы с LLM
import ollama

# Импорт модулей проекта
from core.analysis.multilang_analyzer import MultiLanguageAnalyzer
from tools.large_csharp_analyzer import LargeCSharpAnalyzer
from utils.semantic import QdrantCodeSearch
from utils.embeddings import EmbeddingService
from utils.db_manager import CodeKnowledgeDB

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/telegram_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Константы
OLLAMA_MODEL = "qwen2.5-coder:3b"
VECTOR_STORAGE = "qdrant_storage"
DB_PATH = "data/code_knowledge.db"
MAX_MESSAGE_LENGTH = 4000  # Максимальная длина сообщения в Telegram

class CodeAssistantBot:
    """Телеграм бот для работы с кодом и LLM"""
    
    def __init__(self, token: str):
        """
        Инициализация бота
        
        Args:
            token: Токен для Telegram API
        """
        self.token = token
        self.app = None
        self.chat_history = {}  # История сообщений по пользователям
        self.user_state = {}    # Состояние пользователей
        self.last_active = {}   # Время последней активности пользователей
        
        # Инициализация компонентов
        self.db = CodeKnowledgeDB(DB_PATH)
        self.analyzer = MultiLanguageAnalyzer()
        
        # Инициализация анализатора большого C# проекта
        merged_file = os.environ.get('MERGED_FILE_PATH', 'C:/Users/korda/YandexDisk/steelf/SteelF/merged_code.txt')
        self.large_analyzer = None
        if os.path.exists(merged_file):
            self.large_analyzer = LargeCSharpAnalyzer(merged_file, DB_PATH)
        
        # Инициализация векторного поиска
        self.vector_search = None
        if os.path.exists(merged_file):
            self.vector_search = QdrantCodeSearch(merged_file)
            
        # Команды, которые может выполнять бот
        self.commands = {
            "search": self._cmd_search,
            "analyze": self._cmd_analyze,
            "info": self._cmd_info,
            "status": self._cmd_status,
            "exec": self._cmd_exec,
            "clear": self._cmd_clear
        }
        
        logger.info("Бот инициализирован")
    
    async def start_bot(self):
        """Запуск бота"""
        # Создание приложения
        self.app = Application.builder().token(self.token).build()
        
        # Регистрация обработчиков
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("search", self.cmd_search))
        self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
        self.app.add_handler(CommandHandler("info", self.cmd_info))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("exec", self.cmd_exec))
        self.app.add_handler(CommandHandler("clear", self.cmd_clear))
        
        # Обработчик для обычных сообщений
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Обработчик для callback_query (кнопки)
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Запуск бота
        logger.info("Запуск бота...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        try:
            # Бесконечный цикл для поддержания работы бота
            while True:
                await asyncio.sleep(1)
                
                # Периодическая очистка неактивных чатов
                self._cleanup_inactive_users()
                
        except (KeyboardInterrupt, SystemExit):
            logger.info("Остановка бота...")
            await self.app.stop()
            await self.app.shutdown()
    
    def _cleanup_inactive_users(self):
        """Очистка данных неактивных пользователей"""
        now = time.time()
        inactive_threshold = 3600  # 1 час
        
        inactive_users = []
        for user_id, last_active in self.last_active.items():
            if now - last_active > inactive_threshold:
                inactive_users.append(user_id)
        
        for user_id in inactive_users:
            if user_id in self.chat_history:
                del self.chat_history[user_id]
            if user_id in self.user_state:
                del self.user_state[user_id]
            if user_id in self.last_active:
                del self.last_active[user_id]
    
    def _update_user_activity(self, user_id: int):
        """Обновление времени активности пользователя"""
        self.last_active[user_id] = time.time()
    
    def _get_chat_history(self, user_id: int) -> List[Dict[str, str]]:
        """Получение истории чата пользователя"""
        if user_id not in self.chat_history:
            self.chat_history[user_id] = []
        return self.chat_history[user_id]
    
    def _add_to_chat_history(self, user_id: int, role: str, content: str):
        """Добавление сообщения в историю чата"""
        if user_id not in self.chat_history:
            self.chat_history[user_id] = []
        
        history = self.chat_history[user_id]
        history.append({"role": role, "content": content})
        
        # Ограничение размера истории
        max_history = 20
        if len(history) > max_history:
            self.chat_history[user_id] = history[-max_history:]
    
    def _set_user_state(self, user_id: int, state: Dict[str, Any]):
        """Установка состояния пользователя"""
        self.user_state[user_id] = state
    
    def _get_user_state(self, user_id: int) -> Dict[str, Any]:
        """Получение состояния пользователя"""
        if user_id not in self.user_state:
            self.user_state[user_id] = {}
        return self.user_state[user_id]
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        self._update_user_activity(user_id)
        
        text = ("👋 Добро пожаловать в Code Assistant!\n\n"
                "Я помогу вам работать с кодом C#, анализировать его и получать информацию "
                "о классах, методах и файлах.\n\n"
                "Для получения списка команд используйте /help")
        
        await update.message.reply_text(text)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        user_id = update.effective_user.id
        self._update_user_activity(user_id)
        
        text = ("🔍 *Команды бота*:\n\n"
                "/search <запрос> - Поиск кода по запросу\n"
                "/analyze <файл> - Анализ файла или проекта\n"
                "/info <имя> - Информация о классе, методе или файле\n"
                "/status - Статус системы\n"
                "/exec <команда> - Выполнение команды\n"
                "/clear - Очистка истории чата\n\n"
                
                "📝 *Примеры использования*:\n"
                "/search аутентификация пользователя\n"
                "/info UserController\n"
                "/analyze Program.cs\n")
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /search"""
        user_id = update.effective_user.id
        self._update_user_activity(user_id)
        
        query = ' '.join(context.args) if context.args else ""
        
        if not query:
            await update.message.reply_text("❌ Пожалуйста, укажите запрос для поиска.")
            return
        
        await update.message.reply_text(f"🔍 Поиск: '{query}'...")
        
        try:
            if self.vector_search:
                results = self.vector_search.search_code(query, top_k=3)
                
                if not results:
                    await update.message.reply_text("❌ По вашему запросу ничего не найдено.")
                    return
                
                # Вывод результатов
                for i, result in enumerate(results):
                    text = f"*Результат #{i+1}*\n"
                    text += f"📄 *Файл*: `{result.get('source', 'Неизвестно')}`\n"
                    text += f"💻 *Код*:\n```\n{result.get('text', '')[:1000]}...\n```"
                    
                    # Разбиваем длинные сообщения
                    if len(text) > MAX_MESSAGE_LENGTH:
                        text = text[:MAX_MESSAGE_LENGTH-100] + "...\n```"
                    
                    await update.message.reply_text(text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Векторное хранилище не инициализировано.")
        
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка при поиске: {str(e)}")
    
    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /analyze"""
        user_id = update.effective_user.id
        self._update_user_activity(user_id)
        
        file_path = ' '.join(context.args) if context.args else ""
        
        if not file_path:
            await update.message.reply_text("❌ Пожалуйста, укажите файл для анализа.")
            return
        
        await update.message.reply_text(f"🔍 Анализ файла: '{file_path}'...")
        
        try:
            # Здесь должна быть логика анализа файла
            if self.large_analyzer:
                # Получаем информацию о файле
                info = self.large_analyzer.get_file_info(file_path)
                
                if not info or "error" in info:
                    await update.message.reply_text(f"❌ Файл не найден или ошибка анализа: {info.get('error', 'Неизвестная ошибка')}")
                    return
                
                # Форматирование результата
                text = f"📊 *Анализ файла*: `{file_path}`\n\n"
                text += f"📁 *Язык*: {info.get('language', 'Неизвестно')}\n"
                text += f"📏 *Строк кода*: {info.get('loc', 0)}\n"
                text += f"🔶 *Классы*: {', '.join(info.get('classes', []))}\n"
                text += f"🔷 *Методы*: {', '.join(info.get('methods', []))}\n"
                
                await update.message.reply_text(text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Анализатор не инициализирован.")
        
        except Exception as e:
            logger.error(f"Ошибка при анализе: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка при анализе: {str(e)}")
    
    async def cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /info"""
        user_id = update.effective_user.id
        self._update_user_activity(user_id)
        
        name = ' '.join(context.args) if context.args else ""
        
        if not name:
            await update.message.reply_text("❌ Пожалуйста, укажите имя класса, метода или файла.")
            return
        
        await update.message.reply_text(f"🔍 Поиск информации: '{name}'...")
        
        try:
            if self.large_analyzer:
                # Пробуем найти класс
                class_info = self.large_analyzer.get_class_info(name)
                
                if class_info and "error" not in class_info:
                    # Форматирование информации о классе
                    text = f"📚 *Класс*: `{name}`\n\n"
                    text += f"📁 *Файл*: {class_info.get('file_path', 'Неизвестно')}\n"
                    text += f"🔷 *Пространство имен*: {class_info.get('namespace', 'Неизвестно')}\n"
                    text += f"🔸 *Методы*: {', '.join(class_info.get('methods', []))}\n"
                    
                    await update.message.reply_text(text, parse_mode='Markdown')
                    return
                
                # Пробуем найти метод
                method_info = self.large_analyzer.get_method_info(name)
                
                if method_info and "error" not in method_info:
                    # Форматирование информации о методе
                    text = f"🔧 *Метод*: `{name}`\n\n"
                    text += f"📚 *Класс*: {method_info.get('class_name', 'Неизвестно')}\n"
                    text += f"📁 *Файл*: {method_info.get('file_path', 'Неизвестно')}\n"
                    
                    await update.message.reply_text(text, parse_mode='Markdown')
                    return
                
                # Пробуем найти файл
                file_info = self.large_analyzer.get_file_info(name)
                
                if file_info and "error" not in file_info:
                    # Форматирование информации о файле
                    text = f"📄 *Файл*: `{name}`\n\n"
                    text += f"📁 *Язык*: {file_info.get('language', 'Неизвестно')}\n"
                    text += f"📏 *Строк кода*: {file_info.get('loc', 0)}\n"
                    text += f"🔶 *Классы*: {', '.join(file_info.get('classes', []))}\n"
                    
                    await update.message.reply_text(text, parse_mode='Markdown')
                    return
                
                await update.message.reply_text(f"❌ Информация не найдена: '{name}'")
            else:
                await update.message.reply_text("❌ Анализатор не инициализирован.")
        
        except Exception as e:
            logger.error(f"Ошибка при получении информации: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка при получении информации: {str(e)}")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        user_id = update.effective_user.id
        self._update_user_activity(user_id)
        
        try:
            # Получение статуса системы
            status = {}
            
            # Статус базы данных
            try:
                db_stats = self.db.get_stats() if self.db else None
                status["database"] = db_stats or {"status": "not_initialized"}
            except Exception as e:
                status["database"] = {"status": "error", "message": str(e)}
            
            # Статус анализатора
            try:
                analyzer_ready = self.large_analyzer is not None
                status["analyzer"] = {"status": "ready" if analyzer_ready else "not_initialized"}
            except Exception as e:
                status["analyzer"] = {"status": "error", "message": str(e)}
            
            # Статус векторного поиска
            try:
                vector_ready = self.vector_search is not None
                status["vector_search"] = {"status": "ready" if vector_ready else "not_initialized"}
            except Exception as e:
                status["vector_search"] = {"status": "error", "message": str(e)}
            
            # Форматирование результата
            text = "📊 *Статус системы*\n\n"
            
            # База данных
            db_status = status.get("database", {})
            text += "📁 *База данных*: "
            if db_status.get("status") == "error":
                text += f"❌ Ошибка: {db_status.get('message', 'Неизвестная ошибка')}\n"
            elif db_status.get("status") == "not_initialized":
                text += "⚠️ Не инициализирована\n"
            else:
                text += "✅ Готова\n"
                text += f"  📊 Файлы: {db_status.get('files', 0)}\n"
                text += f"  📊 Классы: {db_status.get('classes', 0)}\n"
                text += f"  📊 Методы: {db_status.get('methods', 0)}\n"
            
            # Анализатор
            analyzer_status = status.get("analyzer", {})
            text += "🔍 *Анализатор*: "
            if analyzer_status.get("status") == "error":
                text += f"❌ Ошибка: {analyzer_status.get('message', 'Неизвестная ошибка')}\n"
            elif analyzer_status.get("status") == "not_initialized":
                text += "⚠️ Не инициализирован\n"
            else:
                text += "✅ Готов\n"
            
            # Векторный поиск
            vector_status = status.get("vector_search", {})
            text += "🔎 *Векторный поиск*: "
            if vector_status.get("status") == "error":
                text += f"❌ Ошибка: {vector_status.get('message', 'Неизвестная ошибка')}\n"
            elif vector_status.get("status") == "not_initialized":
                text += "⚠️ Не инициализирован\n"
            else:
                text += "✅ Готов\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
        
        except Exception as e:
            logger.error(f"Ошибка при получении статуса: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка при получении статуса: {str(e)}")
    
    async def cmd_exec(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /exec"""
        user_id = update.effective_user.id
        self._update_user_activity(user_id)
        
        command = ' '.join(context.args) if context.args else ""
        
        if not command:
            await update.message.reply_text("❌ Пожалуйста, укажите команду для выполнения.")
            return
        
        # Проверка команд на запрещенные операции
        forbidden_cmds = ["rm", "del", "format", "wget", "curl"]
        if any(cmd in command.lower() for cmd in forbidden_cmds):
            await update.message.reply_text("❌ Запрещенная команда.")
            return
        
        await update.message.reply_text(f"⚙️ Выполнение команды: '{command}'...")
        
        try:
            # Выполнение команды в отдельном процессе
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Ожидание завершения с таймаутом
            try:
                stdout, stderr = process.communicate(timeout=30)
                
                # Форматирование результата
                result = ""
                if stdout:
                    result += f"📤 *Вывод*:\n```\n{stdout[:1500]}```\n"
                if stderr:
                    result += f"⚠️ *Ошибки*:\n```\n{stderr[:1500]}```\n"
                
                if not result:
                    result = "✅ Команда выполнена без вывода."
                
                await update.message.reply_text(result, parse_mode='Markdown')
            
            except subprocess.TimeoutExpired:
                process.kill()
                await update.message.reply_text("⚠️ Выполнение команды прервано по таймауту (30 сек).")
        
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка при выполнении команды: {str(e)}")
    
    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /clear"""
        user_id = update.effective_user.id
        self._update_user_activity(user_id)
        
        # Очистка истории чата
        if user_id in self.chat_history:
            self.chat_history[user_id] = []
        
        await update.message.reply_text("🧹 История чата очищена.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик обычных сообщений"""
        user_id = update.effective_user.id
        self._update_user_activity(user_id)
        
        message_text = update.message.text
        
        # Добавление сообщения в историю
        self._add_to_chat_history(user_id, "user", message_text)
        
        # Проверка на команду
        if message_text.startswith('/'):
            command_parts = message_text[1:].split(maxsplit=1)
            command = command_parts[0].lower()
            args = command_parts[1] if len(command_parts) > 1 else ""
            
            if command in self.commands:
                # Выполнение команды
                await self.commands[command](update, context, args)
                return
        
        # Поиск кодового блока в сообщении
        code_blocks = re.findall(r'```(.+?)```', message_text, re.DOTALL)
        
        if code_blocks:
            # Если найден блок кода, выполняем его анализ
            await update.message.reply_text("🔍 Анализ кода...")
            
            for code in code_blocks:
                # Определение языка программирования
                language = "unknown"
                if re.search(r'class\s+\w+|namespace\s+\w+', code):
                    language = "csharp"
                elif re.search(r'public\s+class\s+\w+|import\s+java\.', code):
                    language = "java"
                elif re.search(r'function\s+\w+\s*\(|const\s+\w+\s*=', code):
                    language = "javascript"
                
                # Создание временного файла для анализа
                temp_dir = Path("data/temp")
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = int(time.time())
                ext = ".cs" if language == "csharp" else ".java" if language == "java" else ".js"
                temp_file = temp_dir / f"temp_{timestamp}{ext}"
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                try:
                    # Анализ файла
                    result = self.analyzer.analyze(str(temp_file))
                    
                    # Удаление временного файла
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                    
                    # Форматирование результата
                    text = f"📊 *Анализ кода ({language})*\n\n"
                    
                    if "classes" in result and result["classes"]:
                        text += f"🔶 *Классы*: {', '.join(result.get('classes', []))}\n"
                    
                    if "methods" in result and result["methods"]:
                        text += f"🔷 *Методы*: {', '.join(result.get('methods', []))}\n"
                    
                    if language == "csharp" and "properties" in result and result["properties"]:
                        text += f"🔸 *Свойства*: {', '.join(result.get('properties', []))}\n"
                    
                    if language == "java" and "fields" in result and result["fields"]:
                        text += f"🔹 *Поля*: {', '.join(result.get('fields', []))}\n"
                    
                    if language == "javascript" and "functions" in result and result["functions"]:
                        text += f"🔻 *Функции*: {', '.join(result.get('functions', []))}\n"
                    
                    await update.message.reply_text(text, parse_mode='Markdown')
                    
                except Exception as e:
                    logger.error(f"Ошибка при анализе кода: {str(e)}")
                    await update.message.reply_text(f"❌ Ошибка при анализе кода: {str(e)}")
        else:
            # Если нет кодового блока, обрабатываем как обычный запрос к LLM
            await self._process_llm_query(update, context, message_text)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback_query (нажатие на кнопки)"""
        query = update.callback_query
        user_id = query.from_user.id
        self._update_user_activity(user_id)
        
        # Обработка различных callback
        if query.data.startswith('search_'):
            # Поиск кода
            search_query = query.data.replace('search_', '')
            await query.answer(f"Поиск: {search_query}")
            
            # Подготовка контекста
            context.args = [search_query]
            
            # Вызов команды поиска
            await self.cmd_search(update, context)
        
        elif query.data.startswith('info_'):
            # Информация об объекте
            info_query = query.data.replace('info_', '')
            await query.answer(f"Информация: {info_query}")
            
            # Подготовка контекста
            context.args = [info_query]
            
            # Вызов команды info
            await self.cmd_info(update, context)
    
    async def _process_llm_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
        """Обработка запроса к LLM"""
        user_id = update.effective_user.id
        
        try:
            # Сообщение о начале обработки
            await update.message.reply_text("🤖 Обработка запроса...")
            
            # Получение истории чата
            history = self._get_chat_history(user_id)
            
            # Формирование запроса для LLM
            messages = [
                {"role": "system", "content": "Вы - ассистент для работы с кодом C#. Отвечайте кратко и по существу."},
            ]
            
            # Добавление истории чата (до 5 последних сообщений)
            for message in history[-5:]:
                messages.append(message)
            
            # Добавление дополнительного контекста, если запрос связан с кодом
            if self.vector_search and any(term in query.lower() for term in ['код', 'класс', 'метод', 'функция', 'c#', 'cs']):
                try:
                    # Поиск релевантного кода
                    search_results = self.vector_search.search_code(query, top_k=1)
                    
                    if search_results:
                        context_text = f"Релевантный код:\n```\n{search_results[0].get('text', '')}```\n"
                        messages.append({"role": "system", "content": context_text})
                except Exception as e:
                    logger.error(f"Ошибка при поиске контекста: {str(e)}")
            
            # Запрос к LLM
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages
            )
            
            # Получение ответа
            answer = response.get("message", {}).get("content", "Не удалось получить ответ.")
            
            # Добавление ответа в историю чата
            self._add_to_chat_history(user_id, "assistant", answer)
            
            # Отправка ответа
            await update.message.reply_text(answer, parse_mode='Markdown')
            
            # Добавление кнопок для дополнительных действий
            if len(answer) > 50:
                # Выделение ключевых слов из ответа для поиска
                keywords = re.findall(r'\b([A-Z][a-zA-Z0-9]+)\b', answer)
                keywords = list(set(keywords))[:3]  # Уникальные, не более 3
                
                if keywords:
                    keyboard = []
                    for keyword in keywords:
                        keyboard.append([
                            InlineKeyboardButton(f"🔍 Поиск: {keyword}", callback_data=f"search_{keyword}"),
                            InlineKeyboardButton(f"ℹ️ Инфо: {keyword}", callback_data=f"info_{keyword}")
                        ])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text("Дополнительные действия:", reply_markup=reply_markup)
        
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса к LLM: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка при обработке запроса: {str(e)}")
    
    async def _cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: str):
        """Внутренний обработчик команды search"""
        context.args = args.split()
        await self.cmd_search(update, context)
    
    async def _cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: str):
        """Внутренний обработчик команды analyze"""
        context.args = args.split()
        await self.cmd_analyze(update, context)
    
    async def _cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: str):
        """Внутренний обработчик команды info"""
        context.args = args.split()
        await self.cmd_info(update, context)
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: str):
        """Внутренний обработчик команды status"""
        await self.cmd_status(update, context)
    
    async def _cmd_exec(self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: str):
        """Внутренний обработчик команды exec"""
        context.args = args.split()
        await self.cmd_exec(update, context)
    
    async def _cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: str):
        """Внутренний обработчик команды clear"""
        await self.cmd_clear(update, context)


def main():
    """Основная функция для запуска бота"""
    import argparse
    from dotenv import load_dotenv
    
    # Загрузка переменных окружения
    load_dotenv()
    
    # Получение токена для Telegram API
    token = os.environ.get('TELEGRAM_TOKEN')
    
    if not token:
        print("❌ Ошибка: Не указан токен для Telegram API в переменной TELEGRAM_TOKEN")
        sys.exit(1)
    
    # Создание и запуск бота
    bot = CodeAssistantBot(token)
    
    try:
        asyncio.run(bot.start_bot())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем.")


if __name__ == "__main__":
    main() 
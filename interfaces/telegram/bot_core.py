"""
Основной модуль Telegram-бота для интеграции с Code Assistant.
Предоставляет интерфейс для взаимодействия с системой анализа кода через Telegram.
"""

import logging
import asyncio
import csv
import os
import threading
import queue
from datetime import datetime
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
    CallbackContext
)

from interfaces.telegram.keyboards import create_main_menu
from interfaces.telegram.handlers import register_additional_handlers

logger = logging.getLogger(__name__)

# Список ID администраторов (для команд с ограниченным доступом)
ADMIN_IDS = [12345678]  # Замените на реальные ID администраторов

# Доступные команды бота
BOT_COMMANDS = [
    ("search", "Поиск кода по запросу"),
    ("analyze", "Анализ проекта"),
    ("status", "Статус системы"),
    ("help", "Справка по командам"),
    ("terminal", "Выполнить команду в терминале (только для админов)"),
    ("sql", "Выполнить SQL-запрос (только для админов)")
]

def restricted(func):
    """Декоратор для ограничения доступа к функциям бота"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Доступ запрещен. Эта команда доступна только администраторам.")
            return
        return await func(self, update, context)
    return wrapper

def log_user_action(user_id: int, username: str, command: str):
    """Логирование действий пользователя для аналитики"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "user_actions.csv")
    
    file_exists = os.path.exists(log_file)
    with open(log_file, "a", newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "user_id", "username", "action"])
        writer.writerow([datetime.now().isoformat(), user_id, username, command])

class CodeAssistantBot:
    """Основной класс бота для работы с Code Assistant"""
    
    def __init__(self, token: str, code_assistant=None):
        """
        Инициализация бота.
        
        Args:
            token: Токен бота Telegram.
            code_assistant: Экземпляр класса CodeAssistant.
        """
        self.token = token
        self.code_assistant = code_assistant
        self.application = ApplicationBuilder().token(token).build()
        
        # Настройка и регистрация обработчиков команд
        self._setup_handlers()
        
        # Регистрация дополнительных обработчиков
        register_additional_handlers(self.application, self.code_assistant)
        
        # Кэш для хранения состояний пользователей
        self.user_states = {}
        
        logger.info("Telegram bot initialized successfully")
    
    def _setup_handlers(self):
        """Настройка основных обработчиков команд бота"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("search", self.handle_search))
        self.application.add_handler(CommandHandler("analyze", self.handle_analyze))
        self.application.add_handler(CommandHandler("status", self.handle_status))
        self.application.add_handler(CommandHandler("terminal", self.handle_terminal_command))
        self.application.add_handler(CommandHandler("sql", self.handle_sql))
        
        # Обработка обычных сообщений
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        # Обработка нажатий на кнопки
        self.application.add_handler(CallbackQueryHandler(self.handle_button))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        log_user_action(user.id, user.username, "/start")
        
        welcome_text = (
            f"👋 Привет, {user.first_name}! Я Code Assistant - интеллектуальный помощник для анализа кода.\n\n"
            "Я могу помочь вам в анализе C# кода, поиске информации и ответах на вопросы.\n\n"
            "Используйте команду /help для получения списка доступных команд."
        )
        
        # Создание клавиатуры с основными командами
        keyboard = create_main_menu()
        
        await update.message.reply_text(
            welcome_text, 
            reply_markup=keyboard
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        user = update.effective_user
        log_user_action(user.id, user.username, "/help")
        
        help_text = (
            "🔍 *Доступные команды:*\n\n"
            "• /search [запрос] - Поиск кода по запросу\n"
            "• /analyze - Запуск полного анализа проекта\n"
            "• /status - Проверка статуса системы\n"
            "• /help - Эта справка\n\n"
            "*Специальные команды:*\n"
            "• terminal:[команда] - Выполнение команды в терминале\n"
            "• query:[SQL] - Выполнение SQL-запроса\n"
            "• scrape:[url] [селектор] - Получение данных с веб-страницы\n\n"
            "Вы также можете просто написать вопрос о коде, и я постараюсь на него ответить!"
        )
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /search для поиска кода"""
        user = update.effective_user
        query = ' '.join(context.args) if context.args else ""
        
        if not query:
            await update.message.reply_text(
                "⚠️ Пожалуйста, укажите поисковый запрос.\n"
                "Пример: /search методы класса User"
            )
            return
        
        log_user_action(user.id, user.username, f"/search {query}")
        await update.message.reply_text(f"🔍 Ищу код по запросу: {query}...")
        
        try:
            if self.code_assistant:
                # Выполнение поиска через CodeAssistant
                context = self.code_assistant.get_context(query)
                
                # Отправка результатов
                if len(context) > 4000:
                    parts = [context[i:i+4000] for i in range(0, len(context), 4000)]
                    for i, part in enumerate(parts):
                        await update.message.reply_text(
                            f"Часть {i+1}/{len(parts)}:\n{part}"
                        )
                else:
                    await update.message.reply_text(context)
            else:
                await update.message.reply_text(
                    "⚠️ Поисковая система не инициализирована. Пожалуйста, сообщите администратору."
                )
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            await update.message.reply_text(
                f"❌ Произошла ошибка при поиске: {str(e)}"
            )
    
    async def handle_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /analyze для запуска анализа проекта"""
        user = update.effective_user
        log_user_action(user.id, user.username, "/analyze")
        
        await update.message.reply_text("🔍 Запускаю анализ проекта. Это может занять некоторое время...")
        
        # Создание очереди для получения результата из отдельного потока
        result_queue = queue.Queue()
        
        # Функция для выполнения анализа в отдельном потоке
        def run_analysis():
            try:
                if self.code_assistant:
                    result = self.code_assistant.analyze_project()
                    result_queue.put(result)
                else:
                    result_queue.put({
                        "status": "error",
                        "message": "Система анализа не инициализирована"
                    })
            except Exception as e:
                logger.error(f"Analysis error: {str(e)}")
                result_queue.put({
                    "status": "error",
                    "message": f"Ошибка анализа: {str(e)}"
                })
        
        # Запуск анализа в отдельном потоке
        thread = threading.Thread(target=run_analysis)
        thread.start()
        thread.join()
        
        # Получение и отправка результата
        result = result_queue.get()
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
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status для проверки статуса системы"""
        user = update.effective_user
        log_user_action(user.id, user.username, "/status")
        
        if self.code_assistant:
            status = self.code_assistant.get_system_status()
            status_text = (
                f"🖥 Статус системы:\n"
                f"• Размер векторной БД: {status.get('vector_db_size', 'Н/Д')}\n"
                f"• Размер кэша: {status.get('cache_size', 0) // 1024} KB\n"
                f"• Использование памяти: {status.get('memory_usage', 'Н/Д')} MB\n"
                f"• Время работы: {status.get('uptime', 0)} минут\n"
                f"• Последняя ошибка: {status.get('last_error', 'Нет ошибок')}"
            )
        else:
            status_text = "⚠️ Система не инициализирована."
            
        await update.message.reply_text(status_text)
    
    @restricted
    async def handle_terminal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /terminal для выполнения команд в терминале (только для админов)"""
        user = update.effective_user
        command = ' '.join(context.args) if context.args else ""
        
        if not command:
            await update.message.reply_text(
                "⚠️ Пожалуйста, укажите команду для выполнения.\n"
                "Пример: /terminal ls -la"
            )
            return
        
        log_user_action(user.id, user.username, f"/terminal {command}")
        await update.message.reply_text(f"⚙️ Выполняю команду: {command}...")
        
        try:
            if self.code_assistant:
                result = self.code_assistant.terminal.run_command(command)
                
                # Отправка результата
                if len(result) > 4000:
                    # Разбиение длинного результата на части
                    parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
                    for i, part in enumerate(parts):
                        await update.message.reply_text(
                            f"Часть {i+1}/{len(parts)}:\n```\n{part}\n```",
                            parse_mode="Markdown"
                        )
                else:
                    await update.message.reply_text(f"```\n{result}\n```", parse_mode="Markdown")
            else:
                await update.message.reply_text("⚠️ Терминальный сервис не инициализирован.")
                
        except Exception as e:
            logger.error(f"Terminal command error: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка выполнения команды: {str(e)}")
    
    @restricted
    async def handle_sql(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /sql для выполнения SQL-запросов (только для админов)"""
        user = update.effective_user
        query = ' '.join(context.args) if context.args else ""
        
        if not query:
            await update.message.reply_text(
                "⚠️ Пожалуйста, укажите SQL-запрос.\n"
                "Пример: /sql SELECT * FROM classes LIMIT 5"
            )
            return
        
        log_user_action(user.id, user.username, f"/sql {query}")
        await update.message.reply_text(f"🔍 Выполняю SQL-запрос: {query}...")
        
        try:
            if self.code_assistant:
                result = self.code_assistant.database.execute_query(query)
                await update.message.reply_text(f"```\n{result}\n```", parse_mode="Markdown")
            else:
                await update.message.reply_text("⚠️ Сервис базы данных не инициализирован.")
                
        except Exception as e:
            logger.error(f"SQL query error: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка выполнения запроса: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных текстовых сообщений"""
        user = update.effective_user
        message_text = update.message.text
        
        # Логирование входящего сообщения
        log_user_action(user.id, user.username, f"message: {message_text[:20]}...")
        
        # Проверка на специальные команды в формате prefix:command
        if ":" in message_text:
            prefix, command = message_text.split(":", 1)
            prefix = prefix.strip().lower()
            
            if prefix == "terminal":
                # Имитация команды /terminal
                context.args = command.split()
                await self.handle_terminal_command(update, context)
                return
                
            elif prefix == "query":
                # Имитация команды /sql
                context.args = command.split()
                await self.handle_sql(update, context)
                return
                
            elif prefix == "scrape":
                await self.handle_scrape(update, message_text.split(":", 1)[1])
                return
        
        # Обычное сообщение - отправляем запрос в CodeAssistant
        await update.message.reply_text("🤖 Обрабатываю ваш запрос...")
        
        try:
            if self.code_assistant:
                # Создание очереди для получения результата из отдельного потока
                response_queue = queue.Queue()
                
                # Функция для обработки сообщения в отдельном потоке
                def process_message():
                    try:
                        result = self.code_assistant.handle_command(message_text)
                        response_queue.put(result)
                    except Exception as e:
                        logger.error(f"Message processing error: {str(e)}")
                        response_queue.put(f"⚠️ Ошибка обработки сообщения: {str(e)}")
                
                # Запуск обработки в отдельном потоке
                thread = threading.Thread(target=process_message)
                thread.start()
                thread.join()
                
                # Получение и отправка ответа
                response = response_queue.get()
                
                # Разбиение длинного ответа на части
                if len(response) > 4000:
                    parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                    for i, part in enumerate(parts):
                        await update.message.reply_text(f"Часть {i+1}/{len(parts)}:\n{part}")
                else:
                    await update.message.reply_text(response)
            else:
                await update.message.reply_text(
                    "⚠️ Система не инициализирована. Пожалуйста, сообщите администратору."
                )
                
        except Exception as e:
            logger.error(f"Message handling error: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка обработки сообщения: {str(e)}")
    
    async def handle_scrape(self, update: Update, command: str):
        """Обработка команды для скрапинга веб-страницы"""
        try:
            # Парсинг URL и селектора
            parts = command.strip().split()
            if len(parts) < 2:
                await update.message.reply_text(
                    "⚠️ Недостаточно параметров. Формат: scrape:URL SELECTOR"
                )
                return
                
            url = parts[0]
            selector = ' '.join(parts[1:])
            
            await update.message.reply_text(f"🌐 Получаю данные с {url}...")
            
            if self.code_assistant:
                result = self.code_assistant.scraper.scrape(url, selector)
                await update.message.reply_text(f"```\n{result}\n```", parse_mode="Markdown")
            else:
                await update.message.reply_text("⚠️ Сервис скрапинга не инициализирован.")
                
        except Exception as e:
            logger.error(f"Scraping error: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка получения данных: {str(e)}")
    
    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на inline-кнопки"""
        query = update.callback_query
        await query.answer()
        
        # Получение данных из callback_data
        data = query.data
        user = query.from_user
        
        log_user_action(user.id, user.username, f"button: {data}")
        
        if data == "search":
            await query.message.reply_text(
                "🔍 Введите поисковый запрос в формате:\n/search [ваш запрос]"
            )
        elif data == "analyze":
            # Имитация команды /analyze
            await self.handle_analyze(update, context)
        elif data == "status":
            # Имитация команды /status
            await self.handle_status(update, context)
        elif data == "help":
            # Имитация команды /help
            await self.help(update, context)
        else:
            await query.message.reply_text(f"🔍 Выполняю действие: {data}...")
    
    def run(self):
        """Запуск бота"""
        logger.info("Starting Telegram bot")
        self.application.run_polling()
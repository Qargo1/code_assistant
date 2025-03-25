"""
Модуль с обработчиками команд для Telegram-бота.
"""

import logging
from typing import Dict, List, Any, Callable, Optional, Union
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler
)

from .commands import get_help_text, get_command_help

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
AWAITING_QUERY, PROCESSING = range(2)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start.
    Отправляет приветственное сообщение и основную информацию о боте.
    """
    user = update.effective_user
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для анализа кодовой базы. Могу помочь вам найти информацию о классах, "
        "методах и примерах использования кода.\n\n"
        "Используйте /help для списка доступных команд."
    )
    
    # Создаем клавиатуру с основными командами
    keyboard = [
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("📋 Список классов", callback_data="classes")
        ],
        [
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_markdown(welcome_text, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /help.
    Отправляет список доступных команд или подробную информацию о конкретной команде.
    """
    # Проверяем, есть ли аргументы для получения помощи по конкретной команде
    if context.args and len(context.args) > 0:
        command_name = context.args[0]
        help_text = get_command_help(command_name)
        
        if help_text:
            await update.message.reply_markdown(help_text)
        else:
            await update.message.reply_text(
                f"Команда /{command_name} не найдена. Используйте /help для списка доступных команд."
            )
    else:
        # Отправляем общую справку
        await update.message.reply_markdown(get_help_text())


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /stats.
    Отправляет статистику по кодовой базе.
    """
    try:
        # Заглушка для получения статистики
        # В реальной системе здесь будет запрос к базе данных
        stats = {
            "total_classes": 42,
            "total_methods": 156,
            "total_files": 23,
            "total_usages": 78
        }
        
        stats_text = (
            "*📊 Статистика по кодовой базе:*\n\n"
            f"📁 Файлов: {stats['total_files']}\n"
            f"🧩 Классов: {stats['total_classes']}\n"
            f"⚙️ Методов: {stats['total_methods']}\n"
            f"🔄 Использований: {stats['total_usages']}\n\n"
            "_Данные обновлены: сегодня_"
        )
        
        await update.message.reply_markdown(stats_text)
        
    except Exception as e:
        logger.error(f"Error in stats handler: {str(e)}")
        await update.message.reply_text(
            "😔 Не удалось получить статистику. Пожалуйста, попробуйте позже."
        )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /file.
    Отправляет информацию о классах и методах в указанном файле.
    """
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "Пожалуйста, укажите путь к файлу. Например: `/file path/to/file.py`"
        )
        return
    
    file_path = " ".join(context.args)
    
    try:
        # Заглушка для получения информации о файле
        # В реальной системе здесь будет анализ файла
        file_info = {
            "path": file_path,
            "classes": [
                {"name": "ExampleClass", "methods": 5},
                {"name": "AnotherClass", "methods": 3}
            ],
            "total_lines": 120
        }
        
        response = (
            f"*📄 Информация о файле:* `{file_path}`\n\n"
            f"📏 Строк кода: {file_info['total_lines']}\n"
            f"🧩 Классов: {len(file_info['classes'])}\n\n"
            "*Найденные классы:*\n"
        )
        
        for cls in file_info["classes"]:
            response += f"• `{cls['name']}` ({cls['methods']} методов)\n"
        
        response += "\n_Используйте_ `/methods ИмяКласса` _для просмотра методов класса_"
        
        await update.message.reply_markdown(response)
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        await update.message.reply_text(
            f"😔 Не удалось обработать файл {file_path}. Убедитесь, что путь корректен."
        )


async def handle_classes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /classes.
    Отправляет список классов, опционально отфильтрованный по запросу.
    """
    search_query = " ".join(context.args) if context.args else None
    
    try:
        # Заглушка для получения классов
        # В реальной системе здесь будет запрос к базе данных
        classes = [
            {"name": "FileManager", "file": "core/file_manager.py", "methods": 8},
            {"name": "DatabaseHandler", "file": "core/db/handler.py", "methods": 12},
            {"name": "ApiClient", "file": "core/api/client.py", "methods": 5},
            {"name": "Logger", "file": "utils/logging.py", "methods": 3},
            {"name": "ConfigParser", "file": "utils/config.py", "methods": 6}
        ]
        
        # Фильтрация по запросу, если он есть
        if search_query:
            filtered_classes = [
                cls for cls in classes 
                if search_query.lower() in cls["name"].lower() or search_query.lower() in cls["file"].lower()
            ]
            used_classes = filtered_classes
            has_filter = True
        else:
            used_classes = classes
            has_filter = False
        
        if not used_classes:
            await update.message.reply_text(
                f"😔 Классы по запросу '{search_query}' не найдены."
            )
            return
        
        response = (
            f"*🧩 {'Найденные' if has_filter else 'Доступные'} классы:*\n\n"
        )
        
        for idx, cls in enumerate(used_classes[:10], 1):
            response += f"{idx}. `{cls['name']}` - {cls['methods']} методов\n"
            response += f"   📄 {cls['file']}\n\n"
        
        if len(used_classes) > 10:
            response += f"_...и еще {len(used_classes) - 10} классов_\n\n"
        
        response += "_Используйте_ `/methods ИмяКласса` _для просмотра методов класса_"
        
        await update.message.reply_markdown(response)
        
    except Exception as e:
        logger.error(f"Error in classes handler: {str(e)}")
        await update.message.reply_text(
            "😔 Не удалось получить список классов. Пожалуйста, попробуйте позже."
        )


async def handle_methods(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /methods.
    Отправляет список методов указанного класса.
    """
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "Пожалуйста, укажите имя класса. Например: `/methods FileManager`"
        )
        return
    
    class_name = " ".join(context.args)
    
    try:
        # Заглушка для получения методов класса
        # В реальной системе здесь будет запрос к базе данных
        if class_name == "FileManager":
            methods = [
                {"name": "read_file", "return_type": "str", "params": "file_path: str"},
                {"name": "write_file", "return_type": "bool", "params": "file_path: str, content: str"},
                {"name": "delete_file", "return_type": "bool", "params": "file_path: str"},
                {"name": "copy_file", "return_type": "bool", "params": "source: str, destination: str"},
                {"name": "list_directory", "return_type": "List[str]", "params": "directory: str"}
            ]
        else:
            # Генерируем случайные методы для демонстрации
            methods = [
                {"name": "method1", "return_type": "Any", "params": "param1: int, param2: str"},
                {"name": "method2", "return_type": "bool", "params": ""},
                {"name": "method3", "return_type": "None", "params": "data: Dict[str, Any]"}
            ]
        
        if not methods:
            await update.message.reply_text(
                f"😔 У класса '{class_name}' не найдено методов или класс не существует."
            )
            return
        
        response = (
            f"*⚙️ Методы класса `{class_name}`:*\n\n"
        )
        
        for method in methods:
            response += f"• `{method['name']}({method['params']})` → `{method['return_type']}`\n\n"
        
        response += "_Используйте_ `/sample ИмяКласса.ИмяМетода` _для поиска примеров использования_"
        
        await update.message.reply_markdown(response)
        
    except Exception as e:
        logger.error(f"Error getting methods for class {class_name}: {str(e)}")
        await update.message.reply_text(
            f"😔 Не удалось получить методы класса '{class_name}'. Проверьте правильность имени класса."
        )


async def handle_sample(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /sample.
    Отправляет примеры кода по указанному запросу.
    """
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "Пожалуйста, укажите запрос для поиска примеров. Например: `/sample FileManager.read_file`"
        )
        return
    
    query = " ".join(context.args)
    
    try:
        # Заглушка для поиска примеров
        # В реальной системе здесь будет запрос к базе данных или векторному поиску
        examples = [
            {
                "code": "# Чтение конфигурационного файла\nconfig_content = file_manager.read_file('config.json')\nconfig = json.loads(config_content)",
                "file": "app/config_loader.py",
                "line": 42
            }
        ]
        
        if not examples:
            await update.message.reply_text(
                f"😔 Примеры по запросу '{query}' не найдены."
            )
            return
        
        # Берем первый пример
        example = examples[0]
        
        response = (
            f"*🔍 Пример использования для '{query}':*\n\n"
            f"```python\n{example['code']}\n```\n\n"
            f"📄 Файл: `{example['file']}:{example['line']}`"
        )
        
        await update.message.reply_markdown(response)
        
    except Exception as e:
        logger.error(f"Error searching for sample with query {query}: {str(e)}")
        await update.message.reply_text(
            f"😔 Не удалось найти примеры по запросу '{query}'."
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на инлайн-кнопки."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        await query.message.reply_markdown(get_help_text())
    elif query.data == "stats":
        await handle_stats(update, context)
    elif query.data == "classes":
        # Создаем новый объект Update, так как нам нужно вызвать другой обработчик
        custom_update = Update(update.update_id, message=query.message)
        await handle_classes(custom_update, context)


def register_handlers(application) -> None:
    """
    Регистрирует обработчики команд для приложения Telegram бота.
    
    Args:
        application: Экземпляр приложения Telegram бота
    """
    # Основные команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Регистрация дополнительных обработчиков
    register_additional_handlers(application)
    
    # Обработчик inline кнопок
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Обработчик для неизвестных команд
    application.add_handler(MessageHandler(
        filters.COMMAND, lambda u, c: u.message.reply_text("Неизвестная команда. Используйте /help для списка доступных команд.")
    ))


def register_additional_handlers(application) -> None:
    """
    Регистрирует дополнительные обработчики команд для приложения Telegram бота.
    
    Args:
        application: Экземпляр приложения Telegram бота
    """
    # Команды для работы с кодом
    application.add_handler(CommandHandler("stats", handle_stats))
    application.add_handler(CommandHandler("file", handle_file))
    application.add_handler(CommandHandler("classes", handle_classes))
    application.add_handler(CommandHandler("methods", handle_methods))
    application.add_handler(CommandHandler("sample", handle_sample))
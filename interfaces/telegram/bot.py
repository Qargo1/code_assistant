"""
Модуль для инициализации и запуска Telegram-бота.
"""

import logging
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from telegram import Update, Bot
from telegram.ext import (
    Application, ContextTypes
)

from .handlers import register_handlers
from .commands import get_commands_for_telegram

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/telegram_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Класс для управления Telegram-ботом.
    """
    
    def __init__(self, token: str = None):
        """
        Инициализация бота с токеном.
        
        Args:
            token: Токен доступа к Telegram API, по умолчанию берется из переменных окружения
        """
        # Загрузка переменных окружения, если не загружены
        load_dotenv()
        
        # Получение токена из переменных окружения, если не передан явно
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
            raise ValueError("Токен бота не найден. Укажите его через аргумент или переменную окружения.")
        
        # Инициализация приложения
        self.application = Application.builder().token(self.token).build()
        logger.info("Telegram bot initialized with token")
        
        # Флаг работы бота
        self.is_running = False
    
    async def set_commands(self):
        """
        Устанавливает команды бота в меню Telegram.
        """
        commands = get_commands_for_telegram()
        await self.application.bot.set_my_commands(commands)
        logger.info("Bot commands set successfully")
    
    def register_handlers(self):
        """
        Регистрирует обработчики команд бота.
        """
        register_handlers(self.application)
        logger.info("Handlers registered successfully")
    
    def run(self):
        """
        Запускает бота в режиме polling.
        """
        try:
            logger.info("Starting bot")
            self.register_handlers()
            
            # Устанавливаем команды бота
            asyncio.run(self.set_commands())
            
            # Запускаем бота
            self.is_running = True
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            raise
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = None):
        """
        Отправляет сообщение указанному пользователю.
        
        Args:
            chat_id: ID чата для отправки сообщения
            text: Текст сообщения
            parse_mode: Режим форматирования текста (Markdown, HTML)
        """
        try:
            bot = self.application.bot
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {str(e)}")
            return False


def create_bot():
    """
    Создает и настраивает экземпляр Telegram-бота.
    
    Returns:
        Настроенный экземпляр TelegramBot
    """
    # Создание директории для логов, если её нет
    Path("logs").mkdir(exist_ok=True)
    
    # Создание бота
    try:
        bot = TelegramBot()
        logger.info("Telegram bot created successfully")
        return bot
    except Exception as e:
        logger.error(f"Failed to create Telegram bot: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        # Создание и запуск бота
        telegram_bot = create_bot()
        telegram_bot.run()
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}") 
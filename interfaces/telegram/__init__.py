"""
Пакет для работы с Telegram-ботом.
"""

from .bot import TelegramBot, create_bot
from .handlers import register_handlers

__all__ = ["TelegramBot", "create_bot", "register_handlers"]

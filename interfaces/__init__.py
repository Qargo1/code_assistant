"""
Пакет с различными интерфейсами для взаимодействия с системой анализа кода.
"""

from interfaces.telegram import TelegramBot, create_bot

__all__ = ["TelegramBot", "create_bot"] 
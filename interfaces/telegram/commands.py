"""
Модуль с описанием доступных команд для Telegram-бота.
Содержит константы и структуры данных для формирования списка команд бота.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class BotCommand:
    """Класс представляющий команду Telegram-бота."""
    command: str
    description: str
    detailed_help: str = ""
    
    def get_help(self) -> str:
        """Получить полный текст справки по команде."""
        if self.detailed_help:
            return f"*{self.command}* - {self.description}\n\n{self.detailed_help}"
        return f"*{self.command}* - {self.description}"


# Список команд бота
COMMANDS = [
    BotCommand(
        command="/start",
        description="Начать работу с ботом",
        detailed_help="Используйте эту команду для начала работы с ботом и получения информации о доступных функциях."
    ),
    BotCommand(
        command="/help",
        description="Справка по боту",
        detailed_help="Выводит список всех доступных команд с описанием."
    ),
    BotCommand(
        command="/stats",
        description="Статистика по кодовой базе",
        detailed_help="Показывает общую статистику по кодовой базе: количество классов, методов, файлов и т.д."
    ),
    BotCommand(
        command="/file",
        description="Информация о файле",
        detailed_help="Используйте `/file <путь_к_файлу>` чтобы получить информацию о классах и методах в указанном файле."
    ),
    BotCommand(
        command="/classes",
        description="Список классов",
        detailed_help="Выводит список всех классов в кодовой базе. Используйте `/classes <поисковый_запрос>` для фильтрации по имени класса."
    ),
    BotCommand(
        command="/methods",
        description="Методы класса",
        detailed_help="Используйте `/methods <имя_класса>` для получения списка всех методов указанного класса."
    ),
    BotCommand(
        command="/sample",
        description="Примеры кода",
        detailed_help="Используйте `/sample <запрос>` для поиска примеров кода по указанному запросу."
    )
]


def get_commands_for_telegram() -> List[dict]:
    """
    Возвращает список команд в формате, понятном для регистрации в Telegram API.
    
    Returns:
        Список словарей с ключами 'command' и 'description'
    """
    return [
        {"command": cmd.command.lstrip("/"), "description": cmd.description}
        for cmd in COMMANDS
    ]


def get_help_text() -> str:
    """
    Формирует текст справки со списком всех команд.
    
    Returns:
        Строка с описанием всех команд в формате Markdown
    """
    help_text = "*🤖 Доступные команды:*\n\n"
    
    for cmd in COMMANDS:
        help_text += f"{cmd.command} - {cmd.description}\n"
    
    help_text += "\n_Используйте команду /help <команда> для получения детальной информации о конкретной команде._"
    
    return help_text


def get_command_help(command_name: str) -> Optional[str]:
    """
    Возвращает детальную справку по указанной команде.
    
    Args:
        command_name: Имя команды без слеша в начале или с ним
        
    Returns:
        Текст справки по команде или None, если команда не найдена
    """
    # Нормализация имени команды
    if not command_name.startswith("/"):
        command_name = f"/{command_name}"
    
    for cmd in COMMANDS:
        if cmd.command == command_name:
            return cmd.get_help()
    
    return None 
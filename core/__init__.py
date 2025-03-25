"""
Основной пакет для работы с анализом кода и обработки данных.
Включает в себя модули для анализа кода, работы с базой данных и векторного поиска.
"""

import logging
from pathlib import Path

# Настройка базового логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(Path("logs/core.log")),
        logging.StreamHandler()
    ]
)

# Создаем папку для логов, если она не существует
Path("logs").mkdir(exist_ok=True)

# Экспортируем основные классы для удобства импорта
# Пока это заглушки, поэтому импорты закомментированы
# from core.analysis import FileFilter, chunk_content

__version__ = "0.1.0" 
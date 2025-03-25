"""
Модуль для создания клавиатур в Telegram-боте
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def create_main_menu() -> InlineKeyboardMarkup:
    """
    Создает основное меню с кнопками для быстрого доступа к функциям
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками основных команд
    """
    keyboard = [
        [
            InlineKeyboardButton("🔍 Поиск", callback_data="search"),
            InlineKeyboardButton("📊 Анализ", callback_data="analyze")
        ],
        [
            InlineKeyboardButton("🖥 Статус", callback_data="status"),
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def create_confirmation_keyboard(action_id: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками подтверждения
    
    Args:
        action_id: Идентификатор действия для подтверждения
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{action_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_{action_id}")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def create_pagination_keyboard(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для пагинации результатов
    
    Args:
        current_page: Текущая страница
        total_pages: Общее количество страниц
        prefix: Префикс для callback_data
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками пагинации
    """
    keyboard = []
    
    # Кнопки навигации
    navigation = []
    if current_page > 1:
        navigation.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix}_page_{current_page-1}"))
    
    if current_page < total_pages:
        navigation.append(InlineKeyboardButton("➡️ Вперед", callback_data=f"{prefix}_page_{current_page+1}"))
    
    if navigation:
        keyboard.append(navigation)
    
    # Информация о странице и кнопка закрытия
    keyboard.append([InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="noop")])
    keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search")])
    
    return InlineKeyboardMarkup(keyboard)

def get_file_actions_keyboard(file_path: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Explain", callback_data=f"explain_{file_path}")],
        [InlineKeyboardButton("🔗 Dependencies", callback_data=f"deps_{file_path}")],
        [InlineKeyboardButton("📊 History", callback_data=f"history_{file_path}")]
    ])
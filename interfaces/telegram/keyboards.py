from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search Code", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📊 System Status", callback_data="status")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])

def get_file_actions_keyboard(file_path: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Explain", callback_data=f"explain_{file_path}")],
        [InlineKeyboardButton("🔗 Dependencies", callback_data=f"deps_{file_path}")],
        [InlineKeyboardButton("📊 History", callback_data=f"history_{file_path}")]
    ])
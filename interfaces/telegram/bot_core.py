import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from core.queue.priority_queue import PriorityAnalysisQueue
from core.vector_db.qdrant_connector import VectorSearchEngine

from telegram.ext import Defaults, ExtBot
defaults = Defaults(rate_limit=30)
bot = ExtBot(token=token, defaults=defaults)

ADMIN_IDS = [12345678]

def restricted(func):
    async def wrapper(update, context):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Access denied")
            return
        return await func(update, context)
    return wrapper

import csv
from datetime import datetime

def log_user_action(user_id: int, command: str):
    with open("usage_log.csv", "a") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), user_id, command])

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

class CodeAssistantBot:
    def __init__(self, token: str):
        self.app = ApplicationBuilder().token(token).build()
        self.queue = PriorityAnalysisQueue()
        self.vector_engine = VectorSearchEngine()
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("search", self.handle_search))
        self.app.add_handler(CommandHandler("status", self.handle_status))
        self.app.add_handler(MessageHandler(filters.TEXT, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_button))

    async def start(self, update: Update, _):
        welcome_text = (
            "🚀 Code Analysis Bot Ready!\n\n"
            "Available commands:\n"
            "/search <query> - Find relevant code\n"
            "/status - Show system health\n"
            "/help - Show this message"
        )
        await update.message.reply_text(welcome_text)

    async def handle_search(self, update: Update, context):
        query = ' '.join(context.args)
        if not query:
            await update.message.reply_text("Please enter a search query")
            return
        
        try:
            results = self.vector_engine.search_files(query)
            response = self._format_results(results)
            await update.message.reply_markdown(response)
        except Exception as e:
            logging.error(f"Search failed: {str(e)}")
            await update.message.reply_text("❌ Search failed. Try again later.")

    def _format_results(self, results: list) -> str:
        if not results:
            return "No results found"
            
        return "🔍 Search Results:\n" + "\n".join(
            [f"• [{res['file_path']}]({res['file_path']}) (Score: {res['score']:.2f})" 
             for res in results[:5]]
        )

    async def handle_status(self, update: Update, _):
        status_text = (
            f"🖥 System Status:\n"
            f"• Pending jobs: {self.queue.high_priority.count}\n"
            f"• Vector DB size: {self.vector_engine.client.get_collection().vectors_count}\n"
            f"• Last error: {self._get_last_error()}"
        )
        await update.message.reply_text(status_text)

    def run(self):
        self.app.run_polling()
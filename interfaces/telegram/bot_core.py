import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from core.automation.priority_queue import PriorityAnalysisQueue
from core.vector_db.qdrant_connector import VectorSearchEngine

from telegram.ext import Defaults, ExtBot
defaults = Defaults(rate_limit=30)
bot = ExtBot(token=token, defaults=defaults)

ADMIN_IDS = [12345678]

# Новые команды:
BOT_COMMANDS = [
    ("run_csharp", "Выполнить C# код"),
    ("run_java", "Выполнить Java код"),
    ("convert_to_csharp", "Конвертировать Python в C#"),
    ("next_exercise", "Получить учебное задание"),
    ("visualize_java", "Визуализировать Java классы")
]

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
        self.agent = CodeAssistantAgent()
        self.terminal = TerminalManager()
        self.self_knowledge = SelfKnowledge()
        self._add_self_commands()
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
        
    async def handle_refactor(update: Update, context):
        file_path = context.args[0]
        await update.message.reply_text(f"🔧 Refactoring {file_path}...")
        
        result = refactorer.analyze_file(file_path)
        if result.get('safe'):
            context.bot.send_document(update.chat_id, result['refactored'])
    
    async def handle_message(self, update: Update, context):
        if update.message.text.startswith("/confirm"):
            await self._handle_confirmation(update)
        else:
            await self._handle_agent_query(update)

    async def _handle_agent_query(self, update: Update):
        response = self.agent.process_query(update.message.text, [])
        await update.message.reply_text(response)

    async def _handle_confirmation(self, update: Update):
        user_id = update.effective_user.id
        command = self.terminal.user_confirmations.get(user_id)
        if command:
            output, success = self.terminal.execute_command(command, user_id)
            await update.message.reply_text(f"✅ Result:\n{output}")
            
        def _add_self_commands(self):
        self.app.add_handler(CommandHandler("self_structure", self.handle_self_structure))
        self.app.add_handler(CommandHandler("self_file", self.handle_self_file))

    async def handle_self_structure(self, update: Update, context):
        """Показать структуру собственного кода"""
        structure = self.self_knowledge.get_self_structure()
        response = "🧠 Bot Self Structure:\n"
        response += "\n".join([f"- {c['path']}" for c in structure['components'][:10]])
        await update.message.reply_text(response)

    async def handle_self_file(self, update: Update, context):
        """Показать содержимое файла бота"""
        try:
            file_path = " ".join(context.args)
            content = self.self_knowledge.read_self_file(file_path)
            await update.message.reply_text(f"📄 {file_path}\n```\n{content[:1000]}\n```")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_run_csharp(update: Update, context):
        code = " ".join(context.args)
        result = CSharpRunner().run_code(code)
        response = f"🔄 Результат выполнения C# кода:\n"
        response += f"✅ Успешно!\n{result['output']}" if result['success'] else f"❌ Ошибка:\n{result['error']}"
        await update.message.reply_text(response[:4000])  # Ограничение длины

    # Пример обработчика
    async def handle_exercise(update: Update, context):
        topic = " ".join(context.args) or "basics"
        exercise = ExerciseGenerator().get(topic)
        await update.message.reply_text(
            f"🎯 Задание по {topic}:\n{exercise['question']}\n\n"
            f"📝 Шаблон:\n```csharp\n{exercise['template']}\n```"
        )

    def run(self):
        self.app.run_polling()
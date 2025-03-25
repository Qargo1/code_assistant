import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from interfaces.telegram.bot_core import CodeAssistantBot
from interfaces.telegram.handlers import register_additional_handlers


class TestTelegramIntegration(unittest.TestCase):
    """Тесты для интеграции системы с Telegram"""
    
    @patch('interfaces.telegram.bot_core.ApplicationBuilder')
    def setUp(self, mock_app_builder):
        """Подготовка тестового окружения"""
        # Настройка моков для Telegram API
        self.mock_application = MagicMock()
        mock_app_builder.return_value.token.return_value.build.return_value = self.mock_application
        
        # Создание мока CodeAssistant
        self.mock_code_assistant = MagicMock()
        self.mock_code_assistant.get_context.return_value = "Mock context"
        self.mock_code_assistant.handle_command.return_value = "Mock response"
        self.mock_code_assistant.analyze_project.return_value = {
            "status": "success",
            "message": "Mock analysis complete",
            "stats": {
                "classes": 10,
                "methods": 50,
                "files": 5
            }
        }
        
        # Создание экземпляра бота
        self.bot = CodeAssistantBot("mock_token", self.mock_code_assistant)
    
    def test_handler_registration(self):
        """Тест регистрации обработчиков команд"""
        # Проверяем, что все необходимые обработчики зарегистрированы
        add_handler_calls = [call[0][0].__class__.__name__ for call in self.mock_application.add_handler.call_args_list]
        
        # Ожидаем наличие CommandHandler и MessageHandler
        self.assertIn('CommandHandler', str(add_handler_calls))
        self.assertIn('MessageHandler', str(add_handler_calls))
        
        # Проверка количества зарегистрированных обработчиков
        # 1 MessageHandler + 6 CommandHandler из _setup_handlers
        self.assertGreaterEqual(self.mock_application.add_handler.call_count, 7)
    
    @patch('interfaces.telegram.bot_core.Update')
    @patch('interfaces.telegram.bot_core.ContextTypes')
    async def test_start_command(self, mock_context_types, mock_update):
        """Тест обработки команды /start"""
        # Настройка моков
        mock_update.effective_user.first_name = "Test User"
        mock_update.effective_user.id = 12345
        mock_update.effective_user.username = "testuser"
        mock_update.message = AsyncMock()
        
        # Вызов обработчика команды /start
        await self.bot.start(mock_update, mock_context_types.DEFAULT_TYPE)
        
        # Проверка, что ответ был отправлен
        mock_update.message.reply_text.assert_called_once()
        
        # Проверяем содержимое ответа
        args, kwargs = mock_update.message.reply_text.call_args
        self.assertIn("👋 Привет", args[0])
    
    @patch('interfaces.telegram.bot_core.Update')
    @patch('interfaces.telegram.bot_core.ContextTypes')
    async def test_help_command(self, mock_context_types, mock_update):
        """Тест обработки команды /help"""
        # Настройка моков
        mock_update.effective_user.id = 12345
        mock_update.effective_user.username = "testuser"
        mock_update.message = AsyncMock()
        
        # Вызов обработчика команды /help
        await self.bot.help(mock_update, mock_context_types.DEFAULT_TYPE)
        
        # Проверка, что ответ был отправлен
        mock_update.message.reply_text.assert_called_once()
        
        # Проверяем содержимое ответа
        args, kwargs = mock_update.message.reply_text.call_args
        self.assertIn("Доступные команды", args[0])
    
    @patch('interfaces.telegram.bot_core.Update')
    @patch('interfaces.telegram.bot_core.ContextTypes')
    async def test_search_command(self, mock_context_types, mock_update):
        """Тест обработки команды /search"""
        # Настройка моков
        mock_update.effective_user.id = 12345
        mock_update.effective_user.username = "testuser"
        mock_update.message = AsyncMock()
        mock_context_types.DEFAULT_TYPE.args = ["test query"]
        
        # Вызов обработчика команды /search
        await self.bot.handle_search(mock_update, mock_context_types.DEFAULT_TYPE)
        
        # Проверяем, что метод get_context был вызван
        self.mock_code_assistant.get_context.assert_called_once()
        
        # Проверяем, что ответ был отправлен два раза (запрос и результат)
        self.assertEqual(mock_update.message.reply_text.call_count, 2)
    
    @patch('interfaces.telegram.bot_core.queue')
    @patch('interfaces.telegram.bot_core.threading')
    @patch('interfaces.telegram.bot_core.Update')
    @patch('interfaces.telegram.bot_core.ContextTypes')
    async def test_message_handling(self, mock_context_types, mock_update, mock_threading, mock_queue):
        """Тест обработки обычных сообщений"""
        # Настройка моков
        mock_update.message = AsyncMock()
        mock_update.message.text = "Test question"
        mock_queue.Queue.return_value.get.return_value = "Mock answer"
        
        # Вызов обработчика сообщений
        await self.bot.handle_message(mock_update, mock_context_types.DEFAULT_TYPE)
        
        # Проверяем, что поток был создан и запущен
        mock_threading.Thread.assert_called_once()
        mock_threading.Thread.return_value.start.assert_called_once()
        mock_threading.Thread.return_value.join.assert_called_once()
        
        # Проверяем, что ответ был отправлен два раза (уведомление и результат)
        self.assertEqual(mock_update.message.reply_text.call_count, 2)


if __name__ == '__main__':
    unittest.main() 
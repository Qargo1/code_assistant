import pytest
from unittest.mock import Mock, AsyncMock
from interfaces.telegram.bot_core import CodeAssistantBot

@pytest.fixture
def mock_bot():
    bot = CodeAssistantBot("TEST_TOKEN")
    bot.queue = Mock()
    bot.vector_engine = Mock()
    return bot

@pytest.mark.asyncio
async def test_start_command(mock_bot):
    update = Mock()
    context = Mock()
    
    await mock_bot.start(update, context)
    update.message.reply_text.assert_called_with(contains("Available commands"))

@pytest.mark.asyncio
async def test_search_command(mock_bot):
    update = Mock()
    context = Mock(args=["authentication"])
    
    mock_bot.vector_engine.search_files.return_value = [
        {"file_path": "auth.py", "score": 0.92}
    ]
    
    await mock_bot.handle_search(update, context)
    update.message.reply_markdown.assert_called()

@pytest.mark.asyncio
async def test_status_command(mock_bot):
    update = Mock()
    mock_bot.queue.high_priority.count = 5
    mock_bot.vector_engine.client.get_collection.return_value.vectors_count = 100
    
    await mock_bot.handle_status(update, None)
    status_text = update.message.reply_text.call_args[0][0]
    assert "Pending jobs: 5" in status_text
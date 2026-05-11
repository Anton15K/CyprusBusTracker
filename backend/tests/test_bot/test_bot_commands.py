from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Update
from telegram.ext import ContextTypes

from backend.bot.bot import Bot


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def session_factory(mock_session):
    def _factory():
        class AsyncContextManager:
            async def __aenter__(self):
                return mock_session

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return AsyncContextManager()

    return _factory


@pytest.fixture
def bot(session_factory):
    with patch("backend.bot.bot.Application.builder"):
        return Bot(token="123:mock", name="test_bot", session_creating_method=session_factory)


@pytest.mark.asyncio
async def test_start_command(bot, mock_session, mocker):
    # Mock issue_otp
    mocker.patch.object(bot, "issue_otp", return_value="1234")

    update = MagicMock(spec=Update)
    update.effective_user.id = 123
    update.effective_chat.id = 123
    update.message.reply_text = AsyncMock()

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    # Access private method for testing
    await bot._Bot__start_command(update, context)

    update.message.reply_text.assert_called_once()
    assert "1234" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_subscribe_command_success(bot, mock_session, mocker):
    update = MagicMock(spec=Update)
    update.effective_chat.id = 123
    update.effective_user.username = "user"
    update.effective_user.first_name = "First"
    update.message.reply_text = AsyncMock()

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["stop1", "route1", "15"]

    # Mock database functions
    mocker.patch("backend.bot.bot.get_user_info", return_value={})
    mocker.patch("backend.bot.bot.add_user", new_callable=AsyncMock)
    mocker.patch("backend.bot.bot.add_subscription", new_callable=AsyncMock)

    await bot._Bot__subscribe_command(update, context)

    update.message.reply_text.assert_called_once()
    assert "Subscribed" in update.message.reply_text.call_args[0][0]
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_subscriptions_command(bot, mock_session, mocker):
    update = MagicMock(spec=Update)
    update.effective_chat.id = 123
    update.message.reply_text = AsyncMock()

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    subs = [{"id": 1, "stop_id": "stop1", "route_id": "route1"}]
    mocker.patch("backend.bot.bot.get_subscriptions", return_value=subs)

    await bot._Bot__subscriptions_command(update, context)

    update.message.reply_text.assert_called_once()
    assert "Your subscriptions" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_unsubscribe_command_success(bot, mock_session, mocker):
    update = MagicMock(spec=Update)
    update.effective_chat.id = 123
    update.message.reply_text = AsyncMock()

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["1"]

    mocker.patch("backend.bot.bot.remove_subscription", return_value=True)

    await bot._Bot__unsubscribe_command(update, context)

    update.message.reply_text.assert_called_once_with("Unsubscribed successfully.")
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_subscribe_command_invalid_args(bot):
    update = MagicMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    # Missing args
    context.args = ["stop1"]
    await bot._Bot__subscribe_command(update, context)
    assert "Usage" in update.message.reply_text.call_args[0][0]

    # Invalid minutes
    context.args = ["stop1", "route1", "abc"]
    await bot._Bot__subscribe_command(update, context)
    assert "number" in update.message.reply_text.call_args[0][0]

    # Negative minutes
    context.args = ["stop1", "route1", "-5"]
    await bot._Bot__subscribe_command(update, context)
    assert "positive" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_unsubscribe_command_invalid_id(bot):
    update = MagicMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    # No ID
    context.args = []
    await bot._Bot__unsubscribe_command(update, context)
    assert "Usage" in update.message.reply_text.call_args[0][0]

    # Non-numeric ID
    context.args = ["abc"]
    await bot._Bot__unsubscribe_command(update, context)
    assert "number" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_help_command(bot):
    update = MagicMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await bot._Bot__help_command(update, context)
    update.message.reply_text.assert_called_once()
    assert "Available commands" in update.message.reply_text.call_args[0][0]


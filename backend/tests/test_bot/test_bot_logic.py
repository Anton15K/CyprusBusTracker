from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.models.orm import Telegram_User
from backend.bot.bot import Bot


@pytest.fixture
def mock_bot_session():
    """Mock database session for bot tests."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    # add is a synchronous method in SQLAlchemy's AsyncSession
    session.add = MagicMock()
    return session


@pytest.fixture
def session_factory(mock_bot_session):
    """Fixture to provide a session factory that returns the mock session."""

    def _factory():
        class AsyncContextManager:
            async def __aenter__(self):
                return mock_bot_session

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return AsyncContextManager()

    return _factory


@pytest.fixture
def bot(session_factory):
    """Fixture to initialize the Bot with a mocked session factory."""
    return Bot(
        token="12345:mock_token",
        name="test_bot",
        session_creating_method=session_factory,
    )


@pytest.mark.asyncio
async def test_issue_otp_new_user(bot, mock_bot_session):
    """Test issuing an OTP for a user not yet in the database."""
    # Create the result mock that execute will return
    mock_result = MagicMock()  # Use MagicMock for the result
    mock_result.scalar_one_or_none.return_value = None

    # execute itself is async, so its return value (the result) is what get_user_info awaits
    mock_bot_session.execute.return_value = mock_result

    chat = MagicMock()
    chat.id = 12345
    chat.username = "test_user"
    chat.first_name = "Test"

    otp = await bot.issue_otp(chat)

    assert otp is not None
    assert len(otp) == 4
    # Verify add_user and add_code were called via session.add
    assert mock_bot_session.add.call_count == 2
    mock_bot_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_issue_otp_existing_user(bot, mock_bot_session):
    """Test issuing an OTP for an existing user."""
    # Create the user and result mock
    mock_user = MagicMock(spec=Telegram_User)
    mock_user.chat_id = 12345
    mock_user.username = "test_user"
    mock_user.first_name = "Test"
    mock_user.is_active = False
    mock_user.created_at = MagicMock()

    mock_result = MagicMock()  # Use MagicMock for the result
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_bot_session.execute.return_value = mock_result

    chat = MagicMock()
    chat.id = 12345

    otp = await bot.issue_otp(chat)

    assert otp is not None
    # Only add_code should be called, not add_user
    assert mock_bot_session.add.call_count == 1
    mock_bot_session.commit.assert_called_once()

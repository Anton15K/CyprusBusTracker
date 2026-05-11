from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import CYPRUS_TZ
from app.services.notifications import check_and_send_notifications


@pytest.mark.asyncio
async def test_check_and_send_notifications(mocker):
    # Mock app_state with bot
    mock_bot = AsyncMock()
    mock_app_state = MagicMock()
    mock_app_state.telegram_bot = mock_bot

    # Mock db session context manager
    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # Regular mock for add

    mock_session_context = MagicMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_context)
    mocker.patch("app.db.session.db_manager.session_factory", new=mock_factory)

    # Mock external calls
    mocker.patch(
        "app.services.notifications.update_stop_times_and_get_buses", new_callable=AsyncMock
    )

    # Mock subscriptions
    mock_sub = MagicMock()
    mock_sub.id = 1
    mock_sub.chat_id = "123456"
    mock_sub.stop_id = "10"
    mock_sub.route_id = "101"
    mock_sub.notify_minutes_before = 5
    mocker.patch("app.services.notifications.get_active_subscriptions_all", return_value=[mock_sub])

    # Mock SQL result for approaching bus
    # row: arrival_time_secs, trip_id, route_short_name, stop_name
    now = datetime.now(CYPRUS_TZ)
    current_time_secs = now.hour * 3600 + now.minute * 60 + now.second
    mock_row = (current_time_secs + 180, 5000, "101", "Main Stop")  # 3 minutes away

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_session.execute.side_effect = [
        mock_result,  # For the query finding trips
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # For the check log
    ]

    await check_and_send_notifications(mock_app_state)

    # Verify notification sent
    mock_bot.send_message.assert_called_once()
    assert "Bus 101" in mock_bot.send_message.call_args[0][1]

    # Verify log entry added
    assert mock_session.add.called
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_no_notifications_when_no_subs(mocker):
    mock_app_state = MagicMock()
    mock_app_state.telegram_bot = AsyncMock()

    mocker.patch("app.db.session.db_manager.session_factory", return_value=AsyncMock())
    mocker.patch("app.services.notifications.get_active_subscriptions_all", return_value=[])

    await check_and_send_notifications(mock_app_state)
    mock_app_state.telegram_bot.send_message.assert_not_called()

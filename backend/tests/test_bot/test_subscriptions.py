import pytest
from unittest.mock import MagicMock, AsyncMock
from backend.bot.bot import Bot
from backend.bot.bot_db_functions import add_subscription, get_subscriptions, remove_subscription
from backend.app.models.orm import Notification_Subscription

@pytest.fixture
def mock_session():
    session = AsyncMock()
    # session.add is a synchronous method in SQLAlchemy, so we mock it as MagicMock
    # to avoid RuntimeWarnings about unawaited coroutines when using AsyncMock.
    session.add = MagicMock()
    return session

@pytest.mark.asyncio
async def test_subscription_management(mock_session):
    chat_id = 12345
    stop_id = "STOP1"
    route_id = "ROUTE1"

    # 1. Mock duplicate check (first execute call) -> No duplicate found
    mock_result_empty = MagicMock()
    mock_result_empty.scalar_one_or_none.return_value = None
    
    # 2. Mock get_subscriptions result (second execute call)
    mock_sub = MagicMock(spec=Notification_Subscription)
    mock_sub.id = 1
    mock_sub.stop_id = stop_id
    mock_sub.route_id = route_id
    mock_sub.notify_minutes_before = 10
    mock_sub.is_active = True
    
    mock_result_sub = MagicMock()
    mock_result_sub.scalars.return_value.all.return_value = [mock_sub]
    
    # 3. Mock remove_subscription result (third execute call)
    mock_result_delete = MagicMock()
    mock_result_delete.rowcount = 1

    # Sequence of results for session.execute
    mock_session.execute.side_effect = [
        mock_result_empty, # For duplicate check in add_subscription (1st call)
        mock_result_empty, # For duplicate check in add_subscription (2nd call in test)
        mock_result_sub,   # For get_subscriptions
        mock_result_delete # For remove_subscription
    ]

    # Test add_subscription
    await add_subscription(mock_session, chat_id, stop_id, route_id)
    assert mock_session.add.called
    sub = mock_session.add.call_args[0][0]
    assert isinstance(sub, Notification_Subscription)

    # Test add_subscription with minutes
    await add_subscription(mock_session, chat_id, stop_id, route_id, minutes=5)
    sub_with_mins = mock_session.add.call_args[0][0]
    assert sub_with_mins.notify_minutes_before == 5
    
    # Test get_subscriptions
    subs = await get_subscriptions(mock_session, chat_id)
    assert len(subs) == 1
    assert subs[0]["stop_id"] == stop_id

    # Test remove_subscription
    success = await remove_subscription(mock_session, chat_id, 1)
    assert success is True

@pytest.mark.asyncio
async def test_no_duplicate_subscriptions(mock_session):
    chat_id = 12345
    stop_id = "STOP1"
    route_id = "ROUTE1"
    
    # Mock result showing subscription already exists
    mock_sub = MagicMock(spec=Notification_Subscription)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_sub
    mock_session.execute.return_value = mock_result
    
    # Try adding duplicate
    await add_subscription(mock_session, chat_id, stop_id, route_id)
    
    # Verify session.add was NOT called
    assert not mock_session.add.called

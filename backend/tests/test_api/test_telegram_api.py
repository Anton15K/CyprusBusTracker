from unittest.mock import AsyncMock, patch

import pytest
from app.core.auth import COOKIE_NAME, create_access_token


@pytest.mark.asyncio
async def test_verify_otp_success(client, mock_session):
    with patch("app.api.v1.telegram.check_code", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = 123456789  # chat_id

        response = await client.post(
            "/api/telegram/verify_otp", json={"username": "testuser", "otp_code": "1234"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert COOKIE_NAME in response.cookies
        mock_check.assert_called_once()


@pytest.mark.asyncio
async def test_verify_otp_fail(client, mock_session):
    with patch("app.api.v1.telegram.check_code", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = None

        response = await client.post(
            "/api/telegram/verify_otp", json={"username": "testuser", "otp_code": "wrong"}
        )

        assert response.status_code == 400
        assert COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_get_me_authenticated(client, mock_session):
    chat_id = 123456789
    token = create_access_token(chat_id)
    client.cookies.set(COOKIE_NAME, token)

    with patch("app.api.v1.telegram.get_user_info", new_callable=AsyncMock) as mock_get_info:
        mock_get_info.return_value = {"username": "testuser", "chat_id": chat_id}

        response = await client.get("/api/telegram/me")

        assert response.status_code == 200
        assert response.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    # No cookie set
    response = await client.get("/api/telegram/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_web_subscribe_success(client, mock_session):
    chat_id = 123456789
    token = create_access_token(chat_id)
    client.cookies.set(COOKIE_NAME, token)

    with patch("app.api.v1.telegram.add_subscription", new_callable=AsyncMock) as mock_add_sub:
        response = await client.post(
            "/api/telegram/subscribe", json={"stop_id": "stop1", "route_id": "route1", "minutes": 5}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_add_sub.assert_called_once_with(mock_session, chat_id, "stop1", "route1", 5)

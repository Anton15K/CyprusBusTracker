from unittest.mock import AsyncMock

import pytest
from app.api.v1 import buses, routing, stops, telegram
from app.db.session import db_manager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
async def client(mock_session):
    test_app = FastAPI()
    test_app.include_router(buses.router)
    test_app.include_router(stops.router)
    test_app.include_router(routing.router)
    test_app.include_router(telegram.router)

    async def _override_session():
        yield mock_session

    test_app.dependency_overrides[db_manager.scoped_session_dependency] = _override_session

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac

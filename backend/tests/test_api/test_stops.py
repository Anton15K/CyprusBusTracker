from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_trips_within_hour_returns_200(client, mock_session):
    fake_trips = [
        {
            "arrival_time": 5,
            "route_id": 10,
            "route_short_name": "1A",
            "route_long_name": "Nicosia",
            "trip_id": 100,
        }
    ]
    with patch("app.api.v1.stops.get_trips_within_hour", new=AsyncMock(return_value=fake_trips)):
        response = await client.get("/stops/42")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["route_short_name"] == "1A"


@pytest.mark.asyncio
async def test_routes_stopping_at_returns_routes(client, mock_session):
    fake_routes = [{"route_id": 10, "route_short_name": "1A"}]
    with patch("app.api.v1.stops.get_routes_by_stop_id", new=AsyncMock(return_value=fake_routes)):
        response = await client.get("/stops/routes_stopping_at/42")
    assert response.status_code == 200
    assert response.json()[0]["route_id"] == 10

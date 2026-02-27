from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_buses_returns_200_with_list(client, mock_session):
    fake_buses = [
        {"id": 1, "route_id": 10, "route_short_name": "1A", "lat": 35.1, "lon": 33.3}
    ]
    with patch(
        "app.api.v1.buses.update_stop_times_and_get_buses", new=AsyncMock(return_value=fake_buses)
    ):
        response = await client.get("/api/get_buses")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["route_short_name"] == "1A"


@pytest.mark.asyncio
async def test_get_buses_returns_empty_on_error(client, mock_session):
    with patch(
        "app.api.v1.buses.update_stop_times_and_get_buses",
        new=AsyncMock(side_effect=Exception("GTFS-RT unavailable")),
    ):
        response = await client.get("/api/get_buses")
    assert response.status_code == 200
    assert response.json() == []

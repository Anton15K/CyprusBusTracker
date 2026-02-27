from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_make_route_missing_fields(client):
    response = await client.post("/api/make_route", json={"origin": {"lat": 35.0, "lng": 33.0}})
    assert response.status_code == 400
    assert "destination" in response.json()["detail"]


@pytest.mark.asyncio
async def test_make_route_invalid_coords(client):
    payload = {
        "origin": {"lat": "not_a_number", "lng": 33.0},
        "destination": {"lat": 34.9, "lng": 33.1},
    }
    response = await client.post("/api/make_route", json=payload)
    assert response.status_code == 400
    assert "numbers" in response.json()["detail"]


@pytest.mark.asyncio
async def test_make_route_success(client):
    fake_result = [{"node": {"start": "2026-01-01T10:00", "end": "2026-01-01T10:30", "legs": []}}]
    with patch("app.api.v1.routing.query_graphql", new=AsyncMock(return_value=fake_result)):
        payload = {
            "origin": {"lat": 35.16, "lng": 33.36},
            "destination": {"lat": 34.68, "lng": 33.04},
        }
        response = await client.post("/api/make_route", json=payload)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

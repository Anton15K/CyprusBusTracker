import pytest
from unittest.mock import AsyncMock, MagicMock
from app.db import crud
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_get_all_stops_empty(mocker):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.__iter__.return_value = []
    mock_session.execute.return_value = mock_result
    
    stops = await crud.get_all_stops(mock_session)
    assert stops == []
    mock_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_all_stops_with_data(mocker):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_row = MagicMock()
    mock_row.stop_id = 1
    mock_row.stop_name = "Stop 1"
    mock_row.stop_lat = 35.0
    mock_row.stop_lon = 33.0
    
    mock_result = MagicMock()
    mock_result.__iter__.return_value = [mock_row]
    mock_session.execute.return_value = mock_result
    
    stops = await crud.get_all_stops(mock_session)
    assert len(stops) == 1
    assert stops[0]["stop_id"] == 1
    assert stops[0]["stop_name"] == "Stop 1"

@pytest.mark.asyncio
async def test_get_shape_for_bus(mocker):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_pt = MagicMock()
    mock_pt.shape_pt_lat = 35.1
    mock_pt.shape_pt_lon = 33.1
    
    mock_result = MagicMock()
    mock_result.all.return_value = [mock_pt]
    mock_session.execute.return_value = mock_result
    
    shape = await crud.get_shape_for_bus(mock_session, 101)
    assert len(shape) == 1
    assert shape[0]["lat"] == 35.1

@pytest.mark.asyncio
async def test_stops_on_route(mocker):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.all.return_value = [(35.2, 33.2)]
    mock_session.execute.return_value = mock_result
    
    stops = await crud.stops_on_route(mock_session, 101)
    assert len(stops) == 1
    assert stops[0]["stop_lat"] == 35.2

@pytest.mark.asyncio
async def test_get_routes_by_stop_id(mocker):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_row = MagicMock()
    mock_row.route_id = 50
    mock_row.route_short_name = "50"
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_session.execute.return_value = mock_result
    
    routes = await crud.get_routes_by_stop_id(mock_session, 1)
    assert len(routes) == 1
    assert routes[0]["route_id"] == 50

@pytest.mark.asyncio
async def test_get_trips_within_hour(mocker):
    mock_session = AsyncMock(spec=AsyncSession)
    # arrival_time, route_id, route_short_name, route_long_name, trip_id
    mock_row = (36000, 10, "10", "Route 10", 500)
    
    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_session.execute.return_value = mock_result
    
    # Mock datetime to control current_time_seconds
    mock_now = MagicMock()
    mock_now.hour = 9
    mock_now.minute = 0
    mock_now.second = 0
    # 9*3600 = 32400
    mocker.patch("app.db.crud.datetime", mocker.Mock(now=mocker.Mock(return_value=mock_now)))
    
    trips = await crud.get_trips_within_hour(mock_session, 1)
    assert len(trips) == 1
    # 36000 - 32400 = 3600 seconds = 60 minutes
    assert trips[0]["arrival_time"] == 60
    assert trips[0]["route_id"] == 10

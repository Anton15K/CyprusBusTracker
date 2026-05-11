import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from app.services.gtfs_static import GTFSParser

@pytest.mark.asyncio
async def test_gtfs_parser_get_service_id(mocker):
    mock_session = AsyncMock()
    parser = GTFSParser(mock_session, "/tmp/gtfs")
    
    # row["date"] and row["service_id"]
    mocker.patch("os.path.isfile", return_value=True)
    today = "20260511" # Monday, May 11, 2026 as per session_context
    mocker.patch("app.services.gtfs_static.datetime", mocker.Mock(today=mocker.Mock(return_value=mocker.Mock(date=mocker.Mock(return_value=mocker.Mock(strftime=mocker.Mock(return_value=today)))))))
    
    csv_data = "service_id,date,exception_type\n1,20260511,1\n"
    with patch("builtins.open", mock_open(read_data=csv_data)):
        await parser._get_service_id()
        assert parser.service_id == 1

@pytest.mark.asyncio
async def test_gtfs_parser_insert_trips(mocker):
    mock_session = AsyncMock()
    parser = GTFSParser(mock_session, "/tmp/gtfs")
    parser.service_id = 1
    
    mocker.patch("os.path.isfile", return_value=True)
    csv_data = "route_id,service_id,trip_id,trip_headsign,direction_id\n101,1,500,Headsign,0\n"
    with patch("builtins.open", mock_open(read_data=csv_data)):
        await parser._insert_trips()
        assert 101 in parser.routes_used_today
        assert 500 in parser.trips_used_today
        assert mock_session.add.called

@pytest.mark.asyncio
async def test_gtfs_parser_insert_routes(mocker):
    mock_session = AsyncMock()
    parser = GTFSParser(mock_session, "/tmp/gtfs")
    parser.routes_used_today = {101}
    
    mocker.patch("os.path.isfile", return_value=True)
    csv_data = "route_id,route_short_name,route_long_name\n101,101,Long Name\n202,202,Ignored\n"
    with patch("builtins.open", mock_open(read_data=csv_data)):
        await parser._insert_routes()
        assert mock_session.add.call_count == 1

@pytest.mark.asyncio
async def test_gtfs_parser_insert_stops(mocker):
    mock_session = AsyncMock()
    # Mock existing stops check
    mock_result = MagicMock()
    mock_result.scalars.return_value = [10]
    mock_session.execute.return_value = mock_result
    
    parser = GTFSParser(mock_session, "/tmp/gtfs")
    mocker.patch("os.path.isfile", return_value=True)
    csv_data = "stop_id,stop_name,stop_lat,stop_lon,zone_id\n10,Existing,0,0,1\n20,New,35,33,1\n"
    with patch("builtins.open", mock_open(read_data=csv_data)):
        await parser._insert_stops()
        # Only stop 20 should be added
        assert mock_session.add.call_count == 1

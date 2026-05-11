import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.gtfs_realtime import GTFSRealtimeParser
from app.services import gtfs_realtime_pb2

@pytest.fixture
def mock_feed():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1700000000
    entity = feed.entity.add()
    entity.id = "1"
    vehicle = entity.vehicle
    vehicle.trip.route_id = "101"
    vehicle.trip.trip_id = "500"
    vehicle.position.latitude = 35.0
    vehicle.position.longitude = 33.0
    
    entity2 = feed.entity.add()
    entity2.id = "2"
    tu = entity2.trip_update
    tu.trip.trip_id = "500"
    stu = tu.stop_time_update.add()
    stu.stop_id = "10"
    stu.arrival.time = 1700000000
    return feed

@pytest.mark.asyncio
async def test_fetch_gtfs_rt_data_success(mocker, mock_feed):
    mock_session = AsyncMock()
    parser = GTFSRealtimeParser(mock_session, "http://test.com/rt")
    
    mock_response = MagicMock()
    mock_response.content = mock_feed.SerializeToString()
    mocker.patch("requests.get", return_value=mock_response)
    
    await parser.fetch_gtfs_rt_data()
    assert parser.feed is not None
    assert len(parser.feed.entity) == 2

@pytest.mark.asyncio
async def test_get_bus_positions(mocker, mock_feed):
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [(101, "Route 101")]
    mock_session.execute.return_value = mock_result
    
    parser = GTFSRealtimeParser(mock_session, "http://test.com/rt")
    parser.feed = mock_feed
    
    positions = await parser.get_bus_positions()
    assert len(positions) == 1
    assert positions[0]["route_short_name"] == "Route 101"
    assert positions[0]["lat"] == 35.0

@pytest.mark.asyncio
async def test_update_stop_times(mocker, mock_feed):
    mock_session = AsyncMock()
    # Mock existence checks
    mock_session.execute.return_value.scalars.return_value = [500]
    
    parser = GTFSRealtimeParser(mock_session, "http://test.com/rt")
    parser.feed = mock_feed
    
    mocker.patch.object(parser, "_batch_update_stop_times", new_callable=AsyncMock)
    await parser.update_stop_times()
    
    parser._batch_update_stop_times.assert_called_once()
    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_added_trip_logic(mocker):
    feed = gtfs_realtime_pb2.FeedMessage()
    entity = feed.entity.add()
    tu = entity.trip_update
    tu.trip.schedule_relationship = gtfs_realtime_pb2.TripDescriptor.ADDED
    tu.trip.route_id = "202"
    tu.trip.direction_id = 1
    tu.trip.start_time = "10:00:00"
    
    mock_session = AsyncMock()
    # First check_existence returns None
    # Then create_new_trip returns 999
    parser = GTFSRealtimeParser(mock_session, "url")
    parser.feed = feed
    
    mocker.patch.object(parser, "_check_existence_of_trip_id", return_value=None)
    mocker.patch.object(parser, "_create_new_trip_id", return_value=999)
    mocker.patch.object(parser, "_batch_update_stop_times", new_callable=AsyncMock)
    
    await parser.update_stop_times()
    parser._create_new_trip_id.assert_called_once_with(202, 1, "10:00:00")

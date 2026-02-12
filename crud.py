from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo
from datetime import datetime
from sqlalchemy import text
from GTFS_Parsing import GTFSRealtimeParser
from constants import GTFS_REALTIME_API_PATH

CYPRUS_TZ = ZoneInfo("Asia/Nicosia")

def merge(list1, list2):
    index_in_list1 = 0
    index_in_list2 = 0
    list_merged = []
    while index_in_list1 < len(list1) and index_in_list2 < len(list2):
        if list1[index_in_list1][0] < list2[index_in_list2][0]:
            list_merged.append(list1[index_in_list1])
            index_in_list1 += 1
        else:
            list_merged.append(list2[index_in_list2])
            index_in_list2 += 1
    for i in range(index_in_list1, len(list1)):
        list_merged.append(list1[i])
    for i in range(index_in_list2, len(list2)):
        list_merged.append(list2[i])
    return list_merged
    

def merge_sort(arr):
    if len(arr) == 0:
        return []
    if len(arr) == 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)


async def get_all_stops(session: AsyncSession):
    print("entered_stops")
    query = text("""
        SELECT stop_id, stop_name, stop_lat, stop_lon
        FROM stops;
    """)
    stops = await session.execute(query)
    return [{"stop_id": s.stop_id, "stop_name": s.stop_name, "stop_lat": s.stop_lat, "stop_lon": s.stop_lon} for s in stops]

async def update_stop_times_and_get_buses(session: AsyncSession):
    rt_parser = GTFSRealtimeParser(session, GTFS_REALTIME_API_PATH)
    await rt_parser.fetch_gtfs_rt_data()
    await rt_parser.update_stop_times()
    bus_positions = await rt_parser.get_bus_positions()
    return bus_positions

async def get_shape_for_bus(session: AsyncSession, route_id: int):
    """Fetches the shape points for a given route_id."""
    query = text("""
        SELECT shape_pt_lat, shape_pt_lon
        FROM shapes
        WHERE shape_id = :route_id
        ORDER BY shape_pt_sequence;
    """)
    result = await session.execute(query, {"route_id": route_id})
    shape_points = result.all()
    # print(shape_points)
    return [{"lat": point.shape_pt_lat, "lon": point.shape_pt_lon} for point in shape_points]

async def stops_on_route(session: AsyncSession, route_id: int):
    """
    Returns all distinct routes that stop at the given stop_id using pure SQL.
    """
    query = text("""
        SELECT
        s.stop_lat, 
        s.stop_lon
        FROM stops s
        JOIN stop_times st ON s.stop_id = st.stop_id
        JOIN trips t ON st.trip_id = t.trip_id
        WHERE t.route_id = :route_id;
    """)

    result = await session.execute(query, {"route_id": route_id})
    rows = result.all()

    # Convert to list of dicts for easy handling
    stops = [
        {
            "stop_lat": row[0],
            "stop_lon": row[1]
        }
        for row in rows
    ]

    return stops

async def get_routes_by_stop_id(session: AsyncSession, stop_id: int):
    """
    Returns all distinct routes that stop at the given stop_id using pure SQL.
    """
    query = text("""
        SELECT DISTINCT ON (r.route_short_name)
        r.route_id,
        r.route_short_name
        FROM routes r
        JOIN trips t ON r.route_id = t.route_id
        JOIN stop_times st ON t.trip_id = st.trip_id
        WHERE st.stop_id = :stop_id
        ORDER BY r.route_short_name, r.route_id;
    """)

    result = await session.execute(query, {"stop_id": stop_id})
    rows = result.fetchall()

    # Convert to list of dicts for easy handling
    routes = [
        {
            "route_id": row.route_id,
            "route_short_name": row.route_short_name
        }
        for row in rows
    ]

    return routes

def seconds_to_minutes(seconds: int):
    return round(seconds / 60)
async def get_trips_within_hour(session: AsyncSession, stop_id: int, range_within: int = 3600):
    # Get current time and convert to seconds since midnight
    now = datetime.now(CYPRUS_TZ)
    current_time_seconds = now.hour * 3600 + now.minute * 60 + now.second  # Adjust for timezone offset
    one_hour_later_seconds = current_time_seconds + range_within

    # Build the query with an additional join on Route to fetch route_short_name and route_long_name
    query = text("""
        SELECT 
            stop_times.arrival_time,
            trips.route_id,
            routes.route_short_name,
            routes.route_long_name,
            stop_times.trip_id
        FROM stop_times
        JOIN trips ON trips.trip_id = stop_times.trip_id
        JOIN routes ON routes.route_id = trips.route_id
        WHERE stop_times.stop_id = :stop_id
        AND stop_times.arrival_time >= :current_time_seconds
        AND stop_times.arrival_time <= :one_hour_later_seconds;
    """)

    # Execute the query
    result = await session.execute(query, {"stop_id": stop_id, "current_time_seconds": current_time_seconds, "one_hour_later_seconds": one_hour_later_seconds})
    trips = result.all()
    print(trips)
    # return trips
    # print(trips)
    # Group trips by route_id and limit to max 3 per route
    list_of_trips_with_times = []
    trips = merge_sort(trips)
    for el in trips:
        val = {"arrival_time": seconds_to_minutes(el[0] - current_time_seconds), "route_id": el[1], "route_short_name": el[2], "route_long_name": el[3].split(" - ")[-1], "trip_id": el[4]}
        list_of_trips_with_times.append(val)
    return list_of_trips_with_times

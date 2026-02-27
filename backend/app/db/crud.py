import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import CYPRUS_TZ
from app.services.gtfs_realtime import GTFSRealtimeParser

logger = logging.getLogger(__name__)


def seconds_to_minutes(seconds: int) -> int:
    return round(seconds / 60)


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------


async def get_all_stops(session: AsyncSession) -> list[dict]:
    logger.info("Fetching all stops")
    query = text("SELECT stop_id, stop_name, stop_lat, stop_lon FROM stops;")
    result = await session.execute(query)
    return [
        {
            "stop_id": s.stop_id,
            "stop_name": s.stop_name,
            "stop_lat": s.stop_lat,
            "stop_lon": s.stop_lon,
        }
        for s in result
    ]


async def update_stop_times_and_get_buses(
    session: AsyncSession, gtfs_realtime_url: str
) -> list[dict]:
    rt_parser = GTFSRealtimeParser(session, gtfs_realtime_url)
    await rt_parser.fetch_gtfs_rt_data()
    await rt_parser.update_stop_times()
    return await rt_parser.get_bus_positions()


async def get_shape_for_bus(session: AsyncSession, route_id: int) -> list[dict]:
    query = text("""
        SELECT shape_pt_lat, shape_pt_lon
        FROM shapes
        WHERE shape_id = :route_id
        ORDER BY shape_pt_sequence;
    """)
    result = await session.execute(query, {"route_id": route_id})
    return [{"lat": p.shape_pt_lat, "lon": p.shape_pt_lon} for p in result.all()]


async def stops_on_route(session: AsyncSession, route_id: int) -> list[dict]:
    query = text("""
        SELECT s.stop_lat, s.stop_lon
        FROM stops s
        JOIN stop_times st ON s.stop_id = st.stop_id
        JOIN trips t ON st.trip_id = t.trip_id
        WHERE t.route_id = :route_id;
    """)
    result = await session.execute(query, {"route_id": route_id})
    return [{"stop_lat": row[0], "stop_lon": row[1]} for row in result.all()]


async def get_routes_by_stop_id(session: AsyncSession, stop_id: int) -> list[dict]:
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
    return [
        {"route_id": row.route_id, "route_short_name": row.route_short_name}
        for row in result.fetchall()
    ]


async def get_trips_within_hour(
    session: AsyncSession, stop_id: int, range_within: int = 3600
) -> list[dict]:
    now = datetime.now(CYPRUS_TZ)
    current_time_seconds = now.hour * 3600 + now.minute * 60 + now.second
    one_hour_later_seconds = current_time_seconds + range_within

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

    result = await session.execute(
        query,
        {
            "stop_id": stop_id,
            "current_time_seconds": current_time_seconds,
            "one_hour_later_seconds": one_hour_later_seconds,
        },
    )
    trips = sorted(result.all(), key=lambda row: row[0])

    return [
        {
            "arrival_time": seconds_to_minutes(el[0] - current_time_seconds),
            "route_id": el[1],
            "route_short_name": el[2],
            "route_long_name": el[3].split(" - ")[-1],
            "trip_id": el[4],
        }
        for el in trips
    ]
